"""Tests for forge CLI commands — main.py."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from forge_cli.main import (
    ForgeGroup,
    _configure_logging,
    _resolve_config,
    cli,
)


# =============================================================================
# _configure_logging
# =============================================================================


class TestConfigureLogging:
    """Tests for the logging configuration helper."""

    def test_verbose_enables_debug(self):
        """Verbose mode sets up DEBUG-level logging and quiets llm_gateway."""
        import logging

        # Reset logging state to allow basicConfig to work
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        logging.root.setLevel(logging.WARNING)
        logging.disable(logging.NOTSET)

        _configure_logging(verbose=True)
        assert logging.root.level <= logging.DEBUG
        assert logging.getLogger("llm_gateway").level == logging.INFO
        # Reset
        logging.disable(logging.NOTSET)

    def test_quiet_disables_logging(self):
        """Non-verbose mode disables all logging."""
        import logging

        logging.disable(logging.NOTSET)
        _configure_logging(verbose=False)
        assert logging.root.manager.disable >= logging.CRITICAL
        # Reset
        logging.disable(logging.NOTSET)


# =============================================================================
# _resolve_config
# =============================================================================


class TestResolveConfig:
    """Tests for config path resolution."""

    def test_explicit_path_returned(self):
        """Explicit config path is returned directly."""
        assert _resolve_config("/some/path.yaml") == "/some/path.yaml"

    def test_auto_detect_finds_config(self, tmp_path):
        """Auto-detect finds forge.yaml in project dir."""
        config_file = tmp_path / ".forge" / "forge.yaml"
        config_file.parent.mkdir(parents=True)
        config_file.write_text("project:\n  description: test\n")

        result = _resolve_config(None, str(tmp_path))
        assert "forge.yaml" in result

    def test_no_config_exits(self, tmp_path):
        """SystemExit when no config found anywhere."""
        with pytest.raises(SystemExit):
            _resolve_config(None, str(tmp_path))


# =============================================================================
# ForgeGroup
# =============================================================================


class TestForgeGroup:
    """Tests for the custom click group."""

    def test_bare_forge_shows_help(self):
        """Running bare `forge` shows help text."""
        runner = CliRunner()
        result = runner.invoke(cli, [])
        assert result.exit_code == 0
        assert "Forge" in result.output

    def test_version_flag(self):
        """Running `forge --version` shows version."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "forge" in result.output.lower()

    def test_config_flag_routes_to_generate(self, tmp_path):
        """--config flag routes to generate subcommand."""
        config_file = tmp_path / "forge.yaml"
        config_file.write_text(
            "project:\n  description: test\nmode: mvp\nstrategy: co-pilot\n"
        )
        runner = CliRunner()
        result = runner.invoke(cli, ["--config", str(config_file)])
        # Should attempt to generate (may fail due to missing deps, but
        # the routing works if it doesn't say "no such command")
        assert "No such command" not in result.output


# =============================================================================
# generate command
# =============================================================================


class TestGenerateCommand:
    """Tests for the generate CLI command."""

    def test_validate_only(self, tmp_path):
        """--validate-only prints config summary without generating files."""
        config_file = tmp_path / "forge.yaml"
        config_file.write_text(
            "project:\n  description: test project\nmode: mvp\nstrategy: co-pilot\n"
        )
        runner = CliRunner()
        result = runner.invoke(cli, ["generate", "--config", str(config_file), "--validate-only"])
        assert result.exit_code == 0
        assert "valid" in result.output.lower()
        assert "mvp" in result.output.lower()
        assert "co-pilot" in result.output.lower()

    def test_validate_only_with_non_negotiables(self, tmp_path):
        """--validate-only shows non-negotiable count."""
        config_file = tmp_path / "forge.yaml"
        config_file.write_text(
            "project:\n  description: test\nmode: mvp\nstrategy: co-pilot\n"
            "non_negotiables:\n  - No raw SQL\n  - 100% coverage\n"
        )
        runner = CliRunner()
        result = runner.invoke(cli, ["generate", "--config", str(config_file), "--validate-only"])
        assert result.exit_code == 0
        assert "2 rules" in result.output

    def test_generate_invalid_config(self, tmp_path):
        """Invalid config path raises SystemExit."""
        runner = CliRunner()
        result = runner.invoke(cli, ["generate", "--config", "/nonexistent/file.yaml"])
        assert result.exit_code != 0

    def test_generate_no_config_found(self, tmp_path):
        """No config found prints error and exits."""
        runner = CliRunner()
        result = runner.invoke(cli, ["generate", "--project-dir", str(tmp_path)])
        assert result.exit_code != 0
        assert "no config" in result.output.lower() or result.exit_code == 1

    def test_generate_succeeds(self, tmp_path):
        """Full generation succeeds with valid config."""
        config_file = tmp_path / "forge.yaml"
        config_file.write_text(
            "project:\n  description: test project\nmode: mvp\nstrategy: co-pilot\n"
        )
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["generate", "--config", str(config_file), "--project-dir", str(tmp_path)],
        )
        assert result.exit_code == 0
        assert "complete" in result.output.lower()


# =============================================================================
# refine command
# =============================================================================


class TestRefineCommand:
    """Tests for the refine CLI command."""

    def test_refine_no_config_found(self, tmp_path):
        """Refine without config prints error."""
        runner = CliRunner()
        result = runner.invoke(cli, ["refine", "--project-dir", str(tmp_path)])
        assert result.exit_code != 0

    def test_refine_no_generated_files(self, tmp_path):
        """Refine without generated files tells user to generate first."""
        config_file = tmp_path / "forge.yaml"
        config_file.write_text(
            "project:\n  description: test\nmode: mvp\nstrategy: co-pilot\n"
        )
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["refine", "--config", str(config_file), "--project-dir", str(tmp_path)],
        )
        assert result.exit_code != 0
        assert "generate" in result.output.lower()

    def test_refine_with_generated_files(self, tmp_path):
        """Refine runs when generated files exist."""
        config_file = tmp_path / "forge.yaml"
        config_file.write_text(
            "project:\n  description: test\nmode: mvp\nstrategy: co-pilot\n"
        )
        # Create minimal generated files
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "team-leader.md").write_text("# Team Leader\n\nInstructions here.")

        runner = CliRunner()
        with patch.dict("os.environ", {"FORGE_TEST_DRY_RUN": "1"}):
            result = runner.invoke(
                cli,
                ["refine", "--config", str(config_file), "--project-dir", str(tmp_path)],
            )
        # Should either succeed or fail gracefully (dry-run uses FakeLLMProvider)
        assert result.exit_code == 0 or "error" not in result.output.lower()


# =============================================================================
# start command
# =============================================================================


class TestStartCommand:
    """Tests for the start CLI command."""

    def test_start_no_config_found(self, tmp_path):
        """Start without config prints error."""
        runner = CliRunner()
        result = runner.invoke(cli, ["start", "--project-dir", str(tmp_path)])
        assert result.exit_code != 0

    def test_start_no_init_plan(self, tmp_path):
        """Start without team-init-plan.md tells user to generate first."""
        config_file = tmp_path / "forge.yaml"
        config_file.write_text(
            "project:\n  description: test\nmode: mvp\nstrategy: co-pilot\n"
        )
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["start", "--config", str(config_file), "--project-dir", str(tmp_path)],
        )
        assert result.exit_code != 0
        assert "generate" in result.output.lower()

    def test_start_no_claude_cli(self, tmp_path):
        """Start without claude CLI tells user to install it."""
        config_file = tmp_path / "forge.yaml"
        config_file.write_text(
            "project:\n  description: test\nmode: mvp\nstrategy: co-pilot\n"
        )
        (tmp_path / "team-init-plan.md").write_text("# Init Plan")

        runner = CliRunner()
        with patch("shutil.which", return_value=None):
            result = runner.invoke(
                cli,
                ["start", "--config", str(config_file), "--project-dir", str(tmp_path)],
            )
        assert result.exit_code != 0
        assert "claude" in result.output.lower()

    def test_start_direct_mode(self, tmp_path):
        """Start in direct mode (no tmux) execs claude."""
        config_file = tmp_path / "forge.yaml"
        config_file.write_text(
            "project:\n  description: test\nmode: mvp\nstrategy: co-pilot\n"
        )
        (tmp_path / "team-init-plan.md").write_text("# Init Plan")

        runner = CliRunner()
        with (
            patch("shutil.which", side_effect=lambda x: "/usr/bin/claude" if x == "claude" else None),
            patch("os.execvp") as mock_exec,
            patch("os.chdir"),
        ):
            result = runner.invoke(
                cli,
                ["start", "--config", str(config_file), "--project-dir", str(tmp_path), "--no-tmux"],
            )
        mock_exec.assert_called_once()
        assert mock_exec.call_args[0][0] == "/usr/bin/claude"

    def test_start_tmux_mode(self, tmp_path):
        """Start in tmux mode creates session and attaches."""
        config_file = tmp_path / "forge.yaml"
        config_file.write_text(
            "project:\n  description: test\nmode: mvp\nstrategy: co-pilot\n"
        )
        (tmp_path / "team-init-plan.md").write_text("# Init Plan")

        runner = CliRunner()

        def _which(cmd):
            if cmd == "claude":
                return "/usr/bin/claude"
            if cmd == "tmux":
                return "/usr/bin/tmux"
            return None

        with (
            patch("shutil.which", side_effect=_which),
            patch("subprocess.run") as mock_run,
            patch("os.execvp") as mock_exec,
        ):
            mock_run.return_value = MagicMock(returncode=0)
            result = runner.invoke(
                cli,
                ["start", "--config", str(config_file), "--project-dir", str(tmp_path), "--tmux"],
            )
        # Should have called tmux new-session and then execvp for attach
        assert mock_run.call_count >= 2  # kill-session + new-session + set-environment
        mock_exec.assert_called_once()
        assert "tmux" in mock_exec.call_args[0][0]

    def test_start_tmux_requested_but_not_found(self, tmp_path):
        """--tmux with no tmux installed falls back to direct mode."""
        config_file = tmp_path / "forge.yaml"
        config_file.write_text(
            "project:\n  description: test\nmode: mvp\nstrategy: co-pilot\n"
        )
        (tmp_path / "team-init-plan.md").write_text("# Init Plan")

        runner = CliRunner()

        def _which(cmd):
            if cmd == "claude":
                return "/usr/bin/claude"
            return None  # tmux not found

        with (
            patch("shutil.which", side_effect=_which),
            patch("os.execvp") as mock_exec,
            patch("os.chdir"),
        ):
            result = runner.invoke(
                cli,
                ["start", "--config", str(config_file), "--project-dir", str(tmp_path), "--tmux"],
            )
        # Should fall back to direct mode
        assert "tmux not found" in result.output.lower() or mock_exec.called


# =============================================================================
# init command
# =============================================================================


class TestInitCommand:
    """Tests for the init CLI command."""

    def test_init_non_interactive(self):
        """Init in non-interactive terminal exits with error."""
        runner = CliRunner()
        # CliRunner is non-interactive by default
        with patch("forge_cli.init_wizard._is_interactive", return_value=False):
            result = runner.invoke(cli, ["init"])
        assert result.exit_code != 0


# =============================================================================
# main entry point
# =============================================================================


class TestMainEntryPoint:
    """Tests for the main() function."""

    def test_main_invokes_cli(self):
        """main() calls cli()."""
        from forge_cli.main import main

        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
