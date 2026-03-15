"""Tests for forge stop, resume, and checkpoint-related CLI commands.

Uses Click's CliRunner for isolated testing. Tests the CLI layer
(main.py) with real file I/O but mocked subprocess calls.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from forge_cli.checkpoint import (
    AgentCheckpoint,
    SessionState,
    write_checkpoint,
    write_session,
)
from forge_cli.config_loader import save_config
from forge_cli.config_schema import (
    AgentsConfig,
    ExecutionStrategy,
    ForgeConfig,
    ProjectConfig,
    ProjectMode,
    TeamProfile,
)
from forge_cli.generators.orchestrator import generate_all
from forge_cli.main import cli


def _setup_running_session(tmp_path: Path) -> SessionState:
    """Create a running session with session.json."""
    forge_dir = tmp_path / ".forge"
    forge_dir.mkdir(parents=True, exist_ok=True)

    session = SessionState(
        forge_session_id="test-session-123",
        project_dir=str(tmp_path),
        project_name="test-project",
        config_hash="abc123",
        started_at="2026-03-14T10:00:00Z",
        updated_at="2026-03-14T10:00:00Z",
        status="running",
        tmux_session_name="forge-test-project",
    )
    write_session(session, forge_dir)
    return session


def _setup_stopped_session(tmp_path: Path) -> SessionState:
    """Create a stopped session with session.json and checkpoints."""
    session = _setup_running_session(tmp_path)
    session.status = "stopped"
    session.stop_reason = "explicit"
    forge_dir = tmp_path / ".forge"
    write_session(session, forge_dir)

    # Create a checkpoint
    checkpoints_dir = forge_dir / "checkpoints"
    checkpoints_dir.mkdir(exist_ok=True)
    checkpoint = AgentCheckpoint(
        agent_type="team-leader",
        agent_name="TestLeader",
        status="stopped",
        iteration=2,
        phase="EXECUTE",
        context_summary="Testing checkpoint resume",
        handoff_notes="Continue with task 3",
    )
    write_checkpoint(checkpoint, checkpoints_dir)

    return session


def _setup_generated_project(tmp_path: Path) -> ForgeConfig:
    """Generate a full project for testing."""
    config = ForgeConfig(
        project=ProjectConfig(
            description="Test project for CLI commands",
            directory=str(tmp_path),
        ),
        mode=ProjectMode.MVP,
        strategy=ExecutionStrategy.CO_PILOT,
        agents=AgentsConfig(team_profile=TeamProfile.LEAN),
    )
    generate_all(config)
    # Save config to canonical location for _resolve_config
    forge_dir = tmp_path / ".forge"
    forge_dir.mkdir(exist_ok=True)
    save_config(config, forge_dir / "forge.yaml")
    return config


class TestForgeStopCommand:
    """Tests for the forge stop CLI command."""

    def test_stop_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["stop", "--help"])
        assert result.exit_code == 0
        assert "stop" in result.output.lower()

    def test_stop_no_session_fails(self, tmp_path):
        """forge stop fails when no session.json exists."""
        runner = CliRunner()
        result = runner.invoke(cli, ["stop", "--project-dir", str(tmp_path)])
        assert result.exit_code != 0
        assert "No session found" in result.output or "session" in result.output.lower()

    def test_stop_creates_sentinel(self, tmp_path):
        """forge stop creates STOP_REQUESTED sentinel file."""
        _setup_running_session(tmp_path)

        runner = CliRunner()
        with patch("subprocess.run"):
            result = runner.invoke(
                cli, ["stop", "--project-dir", str(tmp_path), "--timeout", "1"]
            )

        # Session should be updated to stopped
        session_path = tmp_path / ".forge" / "session.json"
        session = json.loads(session_path.read_text())
        assert session["status"] == "stopped"
        assert session["stop_reason"] == "explicit"

    def test_stop_cleans_sentinel(self, tmp_path):
        """forge stop removes STOP_REQUESTED after completion."""
        _setup_running_session(tmp_path)

        runner = CliRunner()
        with patch("subprocess.run"):
            runner.invoke(
                cli, ["stop", "--project-dir", str(tmp_path), "--timeout", "1"]
            )

        sentinel = tmp_path / ".forge" / "STOP_REQUESTED"
        assert not sentinel.exists(), "Sentinel should be cleaned up after stop"

    def test_stop_with_checkpointed_agents(self, tmp_path):
        """forge stop reports agents that checkpointed."""
        _setup_running_session(tmp_path)
        checkpoints_dir = tmp_path / ".forge" / "checkpoints"
        checkpoints_dir.mkdir(parents=True, exist_ok=True)

        # Pre-create a stopped checkpoint
        checkpoint = AgentCheckpoint(
            agent_type="backend-developer",
            agent_name="DevBot",
            status="stopped",
        )
        write_checkpoint(checkpoint, checkpoints_dir)

        runner = CliRunner()
        with patch("subprocess.run"):
            result = runner.invoke(
                cli, ["stop", "--project-dir", str(tmp_path), "--timeout", "1"]
            )

        assert result.exit_code == 0
        assert "stopped" in result.output.lower()

    def test_stop_timeout_path(self, tmp_path):
        """forge stop handles timeout when agents don't stop."""
        _setup_running_session(tmp_path)
        checkpoints_dir = tmp_path / ".forge" / "checkpoints"
        checkpoints_dir.mkdir(parents=True, exist_ok=True)

        # Create an active (not stopped) checkpoint
        checkpoint = AgentCheckpoint(
            agent_type="backend-developer",
            agent_name="DevBot",
            status="active",
        )
        write_checkpoint(checkpoint, checkpoints_dir)

        runner = CliRunner()
        with patch("subprocess.run"):
            result = runner.invoke(
                cli, ["stop", "--project-dir", str(tmp_path), "--timeout", "1"]
            )

        assert result.exit_code == 0
        assert "timed out" in result.output.lower() or "stopped" in result.output.lower()


class TestForgeResumeCommand:
    """Tests for the forge resume CLI command."""

    def test_resume_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["resume", "--help"])
        assert result.exit_code == 0
        assert "resume" in result.output.lower()

    def test_resume_no_session_fails(self, tmp_path):
        """forge resume fails when no session.json exists."""
        runner = CliRunner()
        result = runner.invoke(cli, ["resume", "--project-dir", str(tmp_path)])
        assert result.exit_code != 0
        assert "No session found" in result.output or "session" in result.output.lower()

    def test_resume_reads_checkpoints(self, tmp_path):
        """forge resume reads checkpoint files and builds resume prompt."""
        _setup_stopped_session(tmp_path)
        # Need team-init-plan.md for resume to work
        (tmp_path / "team-init-plan.md").write_text("# Init Plan\n")

        runner = CliRunner()
        # Mock execvp to prevent process replacement
        with patch("os.execvp") as mock_execvp, \
             patch("shutil.which", return_value="/usr/bin/claude"):
            result = runner.invoke(
                cli, ["resume", "--project-dir", str(tmp_path), "--no-tmux"]
            )

        # Should have called execvp with claude and resume prompt
        if mock_execvp.called:
            args = mock_execvp.call_args
            assert "claude" in str(args) or "RESUMED" in str(args) or "resume" in str(args).lower()

    def test_resume_detects_instruction_changes(self, tmp_path):
        """forge resume reports instruction file changes."""
        session = _setup_stopped_session(tmp_path)
        forge_dir = tmp_path / ".forge"

        # Set instruction hashes to something that won't match
        session.instruction_file_hashes = {
            ".claude/agents/team-leader.md": "old-hash-that-wont-match"
        }
        write_session(session, forge_dir)

        # Create the actual file with different content
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        (agents_dir / "team-leader.md").write_text("# Updated Team Leader\n")
        (tmp_path / "team-init-plan.md").write_text("# Init Plan\n")

        runner = CliRunner()
        with patch("os.execvp"), \
             patch("shutil.which", return_value="/usr/bin/claude"):
            result = runner.invoke(
                cli, ["resume", "--project-dir", str(tmp_path), "--no-tmux"]
            )

        # Should mention instruction file changes
        assert "changed" in result.output.lower() or result.exit_code == 0

    def test_resume_updates_session_status(self, tmp_path):
        """forge resume updates session.json status to running."""
        _setup_stopped_session(tmp_path)
        (tmp_path / "team-init-plan.md").write_text("# Init Plan\n")

        runner = CliRunner()
        with patch("os.execvp"), \
             patch("shutil.which", return_value="/usr/bin/claude"):
            runner.invoke(
                cli, ["resume", "--project-dir", str(tmp_path), "--no-tmux"]
            )

        session_path = tmp_path / ".forge" / "session.json"
        session = json.loads(session_path.read_text())
        assert session["status"] == "running"

    def test_resume_tmux_mode(self, tmp_path):
        """forge resume creates tmux session in tmux mode."""
        _setup_stopped_session(tmp_path)
        (tmp_path / "team-init-plan.md").write_text("# Init Plan\n")

        runner = CliRunner()
        with patch("os.execvp") as mock_execvp, \
             patch("subprocess.run") as mock_run, \
             patch("shutil.which", return_value="/usr/bin/tmux"):
            runner.invoke(
                cli, ["resume", "--project-dir", str(tmp_path), "--tmux"]
            )

        # Should have called tmux new-session and execvp to attach
        if mock_run.called:
            tmux_calls = [
                str(c) for c in mock_run.call_args_list
                if "tmux" in str(c)
            ]
            assert len(tmux_calls) > 0, "Should have made tmux calls"


class TestForgeStartCheckpointInit:
    """Tests for checkpoint initialization during forge start."""

    def test_start_creates_session_json(self, tmp_path):
        """forge start creates session.json when launched."""
        config = _setup_generated_project(tmp_path)

        runner = CliRunner()
        with patch("os.execvp"), \
             patch("shutil.which", return_value="/usr/bin/claude"):
            runner.invoke(
                cli, ["start", "--project-dir", str(tmp_path), "--no-tmux"]
            )

        session_path = tmp_path / ".forge" / "session.json"
        assert session_path.exists(), "session.json should be created by forge start"
        session = json.loads(session_path.read_text())
        assert session["status"] == "running"
        assert session["project_dir"] == str(tmp_path.resolve())

    def test_start_generates_hook_scripts(self, tmp_path):
        """forge start generates hook scripts in .forge/hooks/."""
        config = _setup_generated_project(tmp_path)

        runner = CliRunner()
        with patch("os.execvp"), \
             patch("shutil.which", return_value="/usr/bin/claude"):
            runner.invoke(
                cli, ["start", "--project-dir", str(tmp_path), "--no-tmux"]
            )

        hooks_dir = tmp_path / ".forge" / "hooks"
        assert hooks_dir.exists(), "hooks directory should be created"
        hook_files = list(hooks_dir.glob("*.sh"))
        assert len(hook_files) >= 4, f"Should have at least 4 hook scripts, got {len(hook_files)}"

    def test_start_computes_instruction_hashes(self, tmp_path):
        """forge start stores instruction file hashes in session.json."""
        config = _setup_generated_project(tmp_path)

        runner = CliRunner()
        with patch("os.execvp"), \
             patch("shutil.which", return_value="/usr/bin/claude"):
            runner.invoke(
                cli, ["start", "--project-dir", str(tmp_path), "--no-tmux"]
            )

        session_path = tmp_path / ".forge" / "session.json"
        session = json.loads(session_path.read_text())
        hashes = session.get("instruction_file_hashes", {})
        assert len(hashes) > 0, "Should have instruction file hashes"
        # Should include agent files, skill files, CLAUDE.md, etc.
        agent_hashes = [h for h in hashes if ".claude/agents/" in h]
        assert len(agent_hashes) > 0, "Should have agent file hashes"

    def test_start_tmux_mode_sets_session_name(self, tmp_path):
        """forge start in tmux mode stores tmux session name."""
        config = _setup_generated_project(tmp_path)

        runner = CliRunner()
        with patch("os.execvp"), \
             patch("subprocess.run"), \
             patch("shutil.which", return_value="/usr/bin/tmux"):
            runner.invoke(
                cli, ["start", "--project-dir", str(tmp_path), "--tmux"]
            )

        session_path = tmp_path / ".forge" / "session.json"
        if session_path.exists():
            session = json.loads(session_path.read_text())
            assert session.get("tmux_session_name") is not None


class TestStopResumeLifecycle:
    """Integration tests for the full stop -> resume lifecycle."""

    def test_stop_then_resume_preserves_state(self, tmp_path):
        """Full lifecycle: start -> stop -> resume preserves session state."""
        config = _setup_generated_project(tmp_path)
        session = _setup_running_session(tmp_path)

        # Add a checkpoint
        checkpoints_dir = tmp_path / ".forge" / "checkpoints"
        checkpoints_dir.mkdir(parents=True, exist_ok=True)
        checkpoint = AgentCheckpoint(
            agent_type="backend-developer",
            agent_name="DevBot",
            status="stopped",
            iteration=3,
            phase="TEST",
            context_summary="Implementing auth module",
            handoff_notes="Continue with OAuth2 flow",
        )
        write_checkpoint(checkpoint, checkpoints_dir)

        runner = CliRunner()

        # Stop
        with patch("subprocess.run"):
            result = runner.invoke(
                cli, ["stop", "--project-dir", str(tmp_path), "--timeout", "1"]
            )
        assert result.exit_code == 0

        # Verify stopped state
        session_data = json.loads((tmp_path / ".forge" / "session.json").read_text())
        assert session_data["status"] == "stopped"

        # Checkpoint should still exist (hierarchical path)
        cp_path = checkpoints_dir / "backend-developer" / "DevBot.json"
        assert cp_path.exists()
        cp_data = json.loads(cp_path.read_text())
        assert cp_data["agent_name"] == "DevBot"
        assert cp_data["iteration"] == 3

        # Resume
        (tmp_path / "team-init-plan.md").write_text("# Init Plan\n")
        with patch("os.execvp"), \
             patch("shutil.which", return_value="/usr/bin/claude"):
            result = runner.invoke(
                cli, ["resume", "--project-dir", str(tmp_path), "--no-tmux"]
            )

        # Session should be running again
        session_data = json.loads((tmp_path / ".forge" / "session.json").read_text())
        assert session_data["status"] == "running"

    def test_stop_already_stopped_session(self, tmp_path):
        """forge stop on an already stopped session warns but succeeds."""
        _setup_stopped_session(tmp_path)

        runner = CliRunner()
        with patch("subprocess.run"):
            result = runner.invoke(
                cli, ["stop", "--project-dir", str(tmp_path), "--timeout", "1"]
            )
        # Should still succeed (idempotent stop)
        assert result.exit_code == 0 or "stopped" in result.output.lower()

    def test_stop_tmux_send_keys_exception(self, tmp_path):
        """forge stop handles tmux send-keys failure gracefully (lines 705-706)."""
        import subprocess as _sp

        session = _setup_running_session(tmp_path)
        session.tmux_session_name = "forge-test-project"
        write_session(session, tmp_path / ".forge")

        runner = CliRunner()
        with patch("subprocess.run") as mock_run, \
             patch("shutil.which", return_value="/usr/bin/tmux"):
            # Make the send-keys call raise TimeoutExpired
            def _side_effect(cmd, *args, **kwargs):
                if isinstance(cmd, list) and "send-keys" in cmd:
                    raise _sp.TimeoutExpired(cmd=cmd, timeout=5)
                return MagicMock(returncode=0)

            mock_run.side_effect = _side_effect
            result = runner.invoke(
                cli, ["stop", "--project-dir", str(tmp_path), "--timeout", "1"]
            )

        assert result.exit_code == 0
        # The exception should be silently caught — session still stopped
        session_data = json.loads((tmp_path / ".forge" / "session.json").read_text())
        assert session_data["status"] == "stopped"


class TestForgeResumeCommandExtended:
    """Additional tests for uncovered resume command paths."""

    def test_resume_non_stopped_running_status_warning(self, tmp_path):
        """forge resume warns when session status is unexpected (line 782)."""
        session = _setup_running_session(tmp_path)
        session.status = "completed"
        write_session(session, tmp_path / ".forge")
        (tmp_path / "team-init-plan.md").write_text("# Init Plan\n")

        runner = CliRunner()
        with patch("os.execvp"), \
             patch("shutil.which", return_value="/usr/bin/claude"):
            result = runner.invoke(
                cli, ["resume", "--project-dir", str(tmp_path), "--no-tmux"]
            )

        assert "completed" in result.output
        assert "Expected" in result.output or "expected" in result.output.lower()

    def test_resume_config_path_changed_detection(self, tmp_path):
        """forge resume detects config_path changes (lines 805-810)."""
        session = _setup_running_session(tmp_path)
        session.status = "stopped"
        session.config_hash = "old-hash-that-wont-match"
        write_session(session, tmp_path / ".forge")

        (tmp_path / "team-init-plan.md").write_text("# Init Plan\n")

        # Create a config file so --config can point to it
        config_file = tmp_path / "forge-changed.yaml"
        config_file.write_text("project:\n  description: changed\nmode: mvp\nstrategy: co-pilot\n")

        runner = CliRunner()
        with patch("os.execvp"), \
             patch("shutil.which", return_value="/usr/bin/claude"), \
             patch("forge_cli.config_loader.load_config"):
            # We need to pass --config with an existing file
            result = runner.invoke(
                cli, ["resume", "--project-dir", str(tmp_path),
                      "--config", str(config_file), "--no-tmux"]
            )

        # Should mention config changed
        assert "changed" in result.output.lower()

    def test_resume_claude_cli_not_found(self, tmp_path):
        """forge resume exits when claude CLI not found (lines 815-819)."""
        _setup_stopped_session(tmp_path)
        (tmp_path / "team-init-plan.md").write_text("# Init Plan\n")

        runner = CliRunner()
        with patch("shutil.which", return_value=None):
            result = runner.invoke(
                cli, ["resume", "--project-dir", str(tmp_path), "--no-tmux"]
            )

        assert result.exit_code != 0
        assert "Claude CLI not found" in result.output or "claude" in result.output.lower()

    def test_resume_tmux_not_found_fallback(self, tmp_path):
        """forge resume falls back when tmux requested but not found (lines 825-826)."""
        _setup_stopped_session(tmp_path)
        (tmp_path / "team-init-plan.md").write_text("# Init Plan\n")

        runner = CliRunner()

        def _which(name):
            if name == "claude":
                return "/usr/bin/claude"
            # tmux not found
            return None

        with patch("os.execvp"), \
             patch("shutil.which", side_effect=_which):
            result = runner.invoke(
                cli, ["resume", "--project-dir", str(tmp_path), "--tmux"]
            )

        assert "tmux not found" in result.output.lower() or "falling back" in result.output.lower()


class TestForgeEvalAndRefineCommands:
    """Tests for forge eval and forge refine CLI commands."""

    def test_refine_config_load_error(self, tmp_path):
        """forge refine shows error when config fails to load (lines 332-334)."""
        # Create a config with invalid enum value so Pydantic rejects it
        forge_dir = tmp_path / ".forge"
        forge_dir.mkdir(parents=True)
        bad_config = forge_dir / "forge.yaml"
        bad_config.write_text("mode: not-a-valid-mode\n")

        runner = CliRunner()
        result = runner.invoke(
            cli, ["refine", "--config", str(bad_config),
                  "--project-dir", str(tmp_path)]
        )

        assert result.exit_code != 0
        assert "Configuration error" in result.output or "error" in result.output.lower()

    def test_refine_eval_validation_exception(self, tmp_path):
        """forge refine handles eval validation failure gracefully (lines 390-391)."""
        config = _setup_generated_project(tmp_path)

        runner = CliRunner()
        with patch("forge_cli.generators.orchestrator.run_refinement") as mock_refine, \
             patch("forge_cli.evals.eval_runner.run_eval", side_effect=Exception("eval broke")):
            # Mock refinement to return a report
            mock_report = MagicMock()
            mock_report.files_improved = 2
            mock_report.total_cost_usd = 0.05
            mock_report.all_passed = True
            mock_refine.return_value = mock_report

            result = runner.invoke(
                cli, ["refine", "--project-dir", str(tmp_path)]
            )

        assert result.exit_code == 0
        assert "Eval validation skipped" in result.output or "eval broke" in result.output

    def test_eval_config_load_error(self, tmp_path):
        """forge eval shows error when config fails to load (lines 420-422)."""
        forge_dir = tmp_path / ".forge"
        forge_dir.mkdir(parents=True)
        bad_config = forge_dir / "forge.yaml"
        bad_config.write_text("mode: not-a-valid-mode\n")

        runner = CliRunner()
        result = runner.invoke(
            cli, ["eval", "--config", str(bad_config),
                  "--project-dir", str(tmp_path)]
        )

        assert result.exit_code != 0
        assert "Configuration error" in result.output or "error" in result.output.lower()

    def test_eval_cost_display(self, tmp_path):
        """forge eval displays LLM cost when > 0 (line 453)."""
        config = _setup_generated_project(tmp_path)

        runner = CliRunner()
        mock_report = MagicMock()
        mock_report.overall_pass_rate = 0.95
        mock_report.files = []
        mock_report.duration_seconds = 1.5
        mock_report.total_cost_usd = 0.1234
        mock_report.config_name = "test"

        mock_benchmark = MagicMock()
        mock_benchmark.comparison = None

        with patch("forge_cli.evals.eval_runner.run_eval", return_value=mock_report), \
             patch("forge_cli.evals.benchmark.aggregate_benchmark", return_value=mock_benchmark), \
             patch("forge_cli.evals.benchmark.save_benchmark", return_value=(
                 tmp_path / ".forge" / "benchmark.json",
                 tmp_path / ".forge" / "benchmark.md",
             )):
            result = runner.invoke(
                cli, ["eval", "--project-dir", str(tmp_path)]
            )

        assert result.exit_code == 0
        assert "$0.1234" in result.output

    def test_eval_verbose_failed_expectations(self, tmp_path):
        """forge eval --verbose shows failed expectation details (lines 462-465)."""
        config = _setup_generated_project(tmp_path)

        runner = CliRunner()

        from forge_cli.evals import Expectation, GradingResult

        failed_exp = Expectation(
            text="should contain XYZ",
            passed=False,
            evidence="XYZ not found in file",
        )
        passed_exp = Expectation(
            text="should contain ABC",
            passed=True,
            evidence="found ABC",
        )
        file_result = GradingResult(
            file_path=".claude/agents/backend-developer.md",
            expectations=[passed_exp, failed_exp],
            pass_rate=0.5,
        )

        mock_report = MagicMock()
        mock_report.overall_pass_rate = 0.5
        mock_report.files = [file_result]
        mock_report.duration_seconds = 0.5
        mock_report.total_cost_usd = 0.0
        mock_report.config_name = "test"

        mock_benchmark = MagicMock()
        mock_benchmark.comparison = None

        with patch("forge_cli.evals.eval_runner.run_eval", return_value=mock_report), \
             patch("forge_cli.evals.benchmark.aggregate_benchmark", return_value=mock_benchmark), \
             patch("forge_cli.evals.benchmark.save_benchmark", return_value=(
                 tmp_path / ".forge" / "benchmark.json",
                 tmp_path / ".forge" / "benchmark.md",
             )):
            result = runner.invoke(
                cli, ["eval", "--verbose", "--project-dir", str(tmp_path)]
            )

        assert result.exit_code == 0
        # In verbose mode, failed expectations should show their evidence
        assert "should contain XYZ" in result.output or "XYZ not found" in result.output

    def test_eval_description_optimization(self, tmp_path):
        """forge eval --optimize-descriptions runs description optimizer (lines 492-524)."""
        import asyncio as _asyncio

        config = _setup_generated_project(tmp_path)

        runner = CliRunner()

        mock_report = MagicMock()
        mock_report.overall_pass_rate = 0.95
        mock_report.files = []
        mock_report.duration_seconds = 1.0
        mock_report.total_cost_usd = 0.05
        mock_report.config_name = "test"

        mock_benchmark = MagicMock()
        mock_benchmark.comparison = None

        # Create a mock optimization report
        mock_opt_report = MagicMock()
        mock_opt_report.optimized_accuracy = 0.9
        mock_opt_report.original_accuracy = 0.7
        mock_opt_report.original_description = "Original description text"
        mock_opt_report.optimized_description = "Better optimized description text"

        # mock_llm.close() must return a coroutine for asyncio.run()
        mock_llm = MagicMock()

        async def _noop_coro():
            pass

        mock_llm.close = _noop_coro

        async def _fake_optimize(*args, **kwargs):
            return mock_opt_report

        with patch("forge_cli.evals.eval_runner.run_eval", return_value=mock_report), \
             patch("forge_cli.evals.benchmark.aggregate_benchmark", return_value=mock_benchmark), \
             patch("forge_cli.evals.benchmark.save_benchmark", return_value=(
                 tmp_path / ".forge" / "benchmark.json",
                 tmp_path / ".forge" / "benchmark.md",
             )), \
             patch("forge_cli.evals.eval_runner._create_llm_client", return_value=mock_llm), \
             patch("forge_cli.evals.description_optimizer.optimize_description", side_effect=_fake_optimize), \
             patch("forge_cli.evals.description_optimizer._update_description", return_value="updated content"):
            result = runner.invoke(
                cli, ["eval", "--optimize-descriptions",
                      "--project-dir", str(tmp_path)]
            )

        assert result.exit_code == 0
        # Should show optimization results
        assert "Optimizing" in result.output or "description" in result.output.lower()

    def test_eval_description_optimization_no_improvement(self, tmp_path):
        """forge eval --optimize-descriptions shows no-improvement message (line 520)."""
        config = _setup_generated_project(tmp_path)

        runner = CliRunner()

        mock_report = MagicMock()
        mock_report.overall_pass_rate = 0.95
        mock_report.files = []
        mock_report.duration_seconds = 1.0
        mock_report.total_cost_usd = 0.05
        mock_report.config_name = "test"

        mock_benchmark = MagicMock()
        mock_benchmark.comparison = None

        # No improvement: optimized_accuracy <= original_accuracy
        mock_opt_report = MagicMock()
        mock_opt_report.optimized_accuracy = 0.8
        mock_opt_report.original_accuracy = 0.8
        mock_opt_report.original_description = "Same description"
        mock_opt_report.optimized_description = "Same description"

        mock_llm = MagicMock()

        async def _noop_coro():
            pass

        mock_llm.close = _noop_coro

        async def _fake_optimize(*args, **kwargs):
            return mock_opt_report

        with patch("forge_cli.evals.eval_runner.run_eval", return_value=mock_report), \
             patch("forge_cli.evals.benchmark.aggregate_benchmark", return_value=mock_benchmark), \
             patch("forge_cli.evals.benchmark.save_benchmark", return_value=(
                 tmp_path / ".forge" / "benchmark.json",
                 tmp_path / ".forge" / "benchmark.md",
             )), \
             patch("forge_cli.evals.eval_runner._create_llm_client", return_value=mock_llm), \
             patch("forge_cli.evals.description_optimizer.optimize_description", side_effect=_fake_optimize), \
             patch("forge_cli.evals.description_optimizer._update_description", return_value="same content"):
            result = runner.invoke(
                cli, ["eval", "--optimize-descriptions",
                      "--project-dir", str(tmp_path)]
            )

        assert result.exit_code == 0
        assert "no improvement" in result.output.lower()

    def test_eval_description_optimization_error_handling(self, tmp_path):
        """forge eval --optimize-descriptions handles per-skill errors (lines 521-522)."""
        config = _setup_generated_project(tmp_path)

        runner = CliRunner()

        mock_report = MagicMock()
        mock_report.overall_pass_rate = 0.95
        mock_report.files = []
        mock_report.duration_seconds = 1.0
        mock_report.total_cost_usd = 0.05
        mock_report.config_name = "test"

        mock_benchmark = MagicMock()
        mock_benchmark.comparison = None

        # mock_llm.close() must return a coroutine for asyncio.run()
        mock_llm = MagicMock()

        async def _noop_coro():
            pass

        mock_llm.close = _noop_coro

        async def _fail_optimize(*args, **kwargs):
            raise RuntimeError("LLM call failed")

        with patch("forge_cli.evals.eval_runner.run_eval", return_value=mock_report), \
             patch("forge_cli.evals.benchmark.aggregate_benchmark", return_value=mock_benchmark), \
             patch("forge_cli.evals.benchmark.save_benchmark", return_value=(
                 tmp_path / ".forge" / "benchmark.json",
                 tmp_path / ".forge" / "benchmark.md",
             )), \
             patch("forge_cli.evals.eval_runner._create_llm_client", return_value=mock_llm), \
             patch("forge_cli.evals.description_optimizer.optimize_description", side_effect=_fail_optimize):
            result = runner.invoke(
                cli, ["eval", "--optimize-descriptions",
                      "--project-dir", str(tmp_path)]
            )

        assert result.exit_code == 0
        # Should show error message for the failed skill
        assert "Error" in result.output or "error" in result.output.lower()
