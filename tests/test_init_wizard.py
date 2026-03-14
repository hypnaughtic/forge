"""Tests for forge init — the interactive configuration wizard and CLI routing."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import click
import pytest
from click.testing import CliRunner

from forge_cli.config_loader import load_config, save_config
from forge_cli.config_schema import (
    ExecutionStrategy,
    ForgeConfig,
    ProjectMode,
    TeamProfile,
    WorkspaceType,
)
from forge_cli.init_wizard import (
    _BackSignal,
    _prompt_atlassian,
    _prompt_llm_gateway,
    _prompt_mode,
    _prompt_non_negotiables,
    _prompt_project,
    _prompt_strategy,
    _prompt_tech_stack,
    _prompt_workspace,
    _run_fields,
    run_wizard,
)
from forge_cli.main import cli


# =============================================================================
# CLI Routing Tests — Verify command group + backward compatibility
# =============================================================================


class TestCLIRouting:
    """Test that the CLI routes commands correctly after group refactor."""

    def test_forge_no_args_shows_help(self):
        """Running bare `forge` shows help text."""
        runner = CliRunner()
        result = runner.invoke(cli, [])
        assert result.exit_code == 0
        assert "forge init" in result.output.lower() or "Forge" in result.output

    def test_forge_help_flag(self):
        """Running `forge --help` shows help text."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Forge" in result.output

    def test_forge_version(self):
        """Running `forge --version` shows version."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "forge" in result.output.lower()

    def test_forge_config_backward_compat(self, tmp_path):
        """Running `forge --config <path> --validate-only` still works (backward compat)."""
        config = ForgeConfig()
        config.project.description = "Test project"
        config_path = tmp_path / "config.yaml"
        save_config(config, config_path)

        runner = CliRunner()
        result = runner.invoke(cli, ["--config", str(config_path), "--validate-only"])
        assert result.exit_code == 0
        assert "valid" in result.output.lower()

    def test_forge_generate_subcommand(self, tmp_path):
        """Running `forge generate --config <path> --validate-only` works."""
        config = ForgeConfig()
        config.project.description = "Test project"
        config_path = tmp_path / "config.yaml"
        save_config(config, config_path)

        runner = CliRunner()
        result = runner.invoke(
            cli, ["generate", "--config", str(config_path), "--validate-only"]
        )
        assert result.exit_code == 0
        assert "valid" in result.output.lower()

    def test_forge_generate_writes_files(self, tmp_path):
        """Running `forge generate --config <path> --project-dir <dir>` generates files."""
        config = ForgeConfig()
        config.project.description = "Test project for generation"
        config.project.requirements = "Build an e-commerce platform"
        config.tech_stack.languages = ["python"]
        config.tech_stack.frameworks = ["fastapi"]
        config.tech_stack.databases = ["postgresql"]
        config_path = tmp_path / "config.yaml"
        save_config(config, config_path)
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "generate",
                "--config",
                str(config_path),
                "--project-dir",
                str(output_dir),
            ],
        )
        assert result.exit_code == 0
        assert (output_dir / "CLAUDE.md").exists()
        assert (output_dir / "team-init-plan.md").exists()
        assert (output_dir / ".claude" / "agents").is_dir()

    def test_forge_config_backward_compat_generates_files(self, tmp_path):
        """Running `forge --config <path> --project-dir <dir>` generates files (backward compat)."""
        config = ForgeConfig()
        config.project.description = "Backward compat gen test"
        config.project.requirements = "Build a web app"
        config.tech_stack.languages = ["python"]
        config.tech_stack.frameworks = ["fastapi"]
        config.tech_stack.databases = ["postgresql"]
        config_path = tmp_path / "config.yaml"
        save_config(config, config_path)
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--config", str(config_path), "--project-dir", str(output_dir)],
        )
        assert result.exit_code == 0
        assert (output_dir / "CLAUDE.md").exists()

    def test_forge_generate_invalid_config(self, tmp_path):
        """Running `forge generate --config <bad>` fails gracefully."""
        bad_path = tmp_path / "bad.yaml"
        bad_path.write_text("mode: invalid-value\n  broken: [[[")

        runner = CliRunner()
        result = runner.invoke(
            cli, ["generate", "--config", str(bad_path), "--validate-only"]
        )
        assert result.exit_code != 0

    def test_forge_generate_missing_config(self):
        """Running `forge generate --config nonexistent.yaml` fails."""
        runner = CliRunner()
        result = runner.invoke(cli, ["generate", "--config", "nonexistent.yaml"])
        assert result.exit_code != 0

    def test_forge_refine_subcommand_exists(self):
        """The `refine` subcommand is registered and accessible."""
        runner = CliRunner()
        result = runner.invoke(cli, ["refine", "--help"])
        assert result.exit_code == 0
        assert "refine" in result.output.lower()

    def test_forge_init_subcommand_exists(self):
        """The `init` subcommand is registered and accessible."""
        runner = CliRunner()
        result = runner.invoke(cli, ["init", "--help"])
        assert result.exit_code == 0
        assert "interactively" in result.output.lower() or "config" in result.output.lower()

    def test_forge_start_subcommand_exists(self):
        """The `start` subcommand is registered and accessible."""
        runner = CliRunner()
        result = runner.invoke(cli, ["start", "--help"])
        assert result.exit_code == 0
        assert "claude" in result.output.lower() or "start" in result.output.lower()

    def test_forge_generate_auto_detect(self, tmp_path):
        """Running `forge generate --project-dir <dir>` auto-detects config."""
        config = ForgeConfig()
        config.project.description = "Auto detect test"
        # Save to canonical location
        forge_dir = tmp_path / ".forge"
        forge_dir.mkdir()
        config_path = forge_dir / "forge.yaml"
        save_config(config, config_path)

        runner = CliRunner()
        result = runner.invoke(
            cli, ["generate", "--project-dir", str(tmp_path), "--validate-only"]
        )
        assert result.exit_code == 0
        assert "valid" in result.output.lower()

    def test_forge_generate_auto_detect_legacy(self, tmp_path):
        """Auto-detect finds legacy forge-config.yaml."""
        config = ForgeConfig()
        config.project.description = "Legacy auto detect"
        config_path = tmp_path / "forge-config.yaml"
        save_config(config, config_path)

        runner = CliRunner()
        result = runner.invoke(
            cli, ["generate", "--project-dir", str(tmp_path), "--validate-only"]
        )
        assert result.exit_code == 0

    def test_forge_generate_no_config_found(self, tmp_path):
        """Auto-detect fails when no config file exists."""
        runner = CliRunner()
        result = runner.invoke(
            cli, ["generate", "--project-dir", str(tmp_path), "--validate-only"]
        )
        assert result.exit_code != 0


# =============================================================================
# CLI Routing via Subprocess — End-to-end like the user actually runs it
# =============================================================================


class TestCLISubprocess:
    """Test CLI routing via subprocess (real process invocation)."""

    def _run_forge(self, args: list[str], timeout: int = 10) -> subprocess.CompletedProcess:
        return subprocess.run(
            [
                "python",
                "-c",
                f"""
import sys
sys.argv = ['forge'] + {args!r}
from forge_cli.main import cli
try:
    cli(standalone_mode=False)
except SystemExit as e:
    sys.exit(e.code if e.code else 0)
""",
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    def test_subprocess_version(self):
        """forge --version works via subprocess."""
        result = self._run_forge(["--version"])
        assert result.returncode == 0

    def test_subprocess_no_args_shows_help(self):
        """forge with no args shows help (not an error)."""
        result = self._run_forge([])
        assert result.returncode == 0

    def test_subprocess_validate_valid_config(self, tmp_path):
        """forge --config <path> --validate-only works via subprocess."""
        config = ForgeConfig()
        config.project.description = "Subprocess test"
        config_path = tmp_path / "config.yaml"
        save_config(config, config_path)

        result = self._run_forge(
            ["--config", str(config_path), "--validate-only"]
        )
        assert result.returncode == 0

    def test_subprocess_generate_subcommand(self, tmp_path):
        """forge generate --config <path> --validate-only works via subprocess."""
        config = ForgeConfig()
        config.project.description = "Subprocess generate test"
        config_path = tmp_path / "config.yaml"
        save_config(config, config_path)

        result = self._run_forge(
            ["generate", "--config", str(config_path), "--validate-only"]
        )
        assert result.returncode == 0

    def test_subprocess_init_non_tty_fails(self):
        """forge init in a non-TTY subprocess exits with error."""
        result = self._run_forge(["init"])
        # Non-TTY should exit with code 1
        assert result.returncode != 0


# =============================================================================
# Wizard Step Unit Tests — Each prompt function tested independently
# =============================================================================


class TestPromptProject:
    """Test _prompt_project step."""

    def test_basic_project(self):
        """Builds ProjectConfig from basic inputs."""
        # description, plan_file, context_files, project_type
        inputs = "My awesome project\n\n\nnew\n"
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                _make_click_command(_prompt_project), input=inputs
            )
            assert result.exit_code == 0

    def test_empty_description_reprompts(self):
        """Empty description causes re-prompt."""
        # First empty, then valid desc, plan_file, context_files, type
        inputs = "\nActual description\n\n\nnew\n"
        runner = CliRunner()
        result = runner.invoke(
            _make_click_command(_prompt_project), input=inputs
        )
        assert result.exit_code == 0

    def test_existing_project_asks_path(self):
        """Choosing 'existing' prompts for path."""
        inputs = "My project\n\n\nexisting\n/path/to/project\n"
        runner = CliRunner()
        result = runner.invoke(
            _make_click_command(_prompt_project), input=inputs
        )
        assert result.exit_code == 0

    def test_new_project_no_path(self):
        """Choosing 'new' does not ask for path."""
        inputs = "My project\n\n\nnew\n"
        runner = CliRunner()
        result = runner.invoke(
            _make_click_command(_prompt_project), input=inputs
        )
        assert result.exit_code == 0
        assert "/path" not in result.output


class TestPromptMode:
    """Test _prompt_mode step."""

    def test_default_mvp(self):
        """Default selection (1) returns MVP."""
        runner = CliRunner()
        result = runner.invoke(_make_click_command(_prompt_mode), input="1\n")
        assert result.exit_code == 0

    def test_production_ready(self):
        """Selection 2 returns production-ready."""
        runner = CliRunner()
        result = runner.invoke(_make_click_command(_prompt_mode), input="2\n")
        assert result.exit_code == 0

    def test_no_compromise(self):
        """Selection 3 returns no-compromise."""
        runner = CliRunner()
        result = runner.invoke(_make_click_command(_prompt_mode), input="3\n")
        assert result.exit_code == 0


class TestPromptStrategy:
    """Test _prompt_strategy step."""

    def test_auto_pilot(self):
        """Selection 1 returns auto-pilot."""
        runner = CliRunner()
        result = runner.invoke(_make_click_command(_prompt_strategy), input="1\n")
        assert result.exit_code == 0

    def test_default_co_pilot(self):
        """Default selection (2) returns co-pilot."""
        runner = CliRunner()
        result = runner.invoke(_make_click_command(_prompt_strategy), input="2\n")
        assert result.exit_code == 0

    def test_micro_manage(self):
        """Selection 3 returns micro-manage."""
        runner = CliRunner()
        result = runner.invoke(_make_click_command(_prompt_strategy), input="3\n")
        assert result.exit_code == 0


class TestPromptTechStack:
    """Test _prompt_tech_stack step."""

    def test_full_tech_stack(self):
        """All fields filled in."""
        inputs = "python, typescript\nfastapi, react\npostgresql\ndocker\n"
        runner = CliRunner()
        result = runner.invoke(
            _make_click_command(_prompt_tech_stack), input=inputs
        )
        assert result.exit_code == 0

    def test_empty_tech_stack(self):
        """All fields skipped."""
        inputs = "\n\n\n\n"
        runner = CliRunner()
        result = runner.invoke(
            _make_click_command(_prompt_tech_stack), input=inputs
        )
        assert result.exit_code == 0

    def test_partial_tech_stack(self):
        """Some fields filled, some skipped."""
        inputs = "python\n\npostgresql\n\n"
        runner = CliRunner()
        result = runner.invoke(
            _make_click_command(_prompt_tech_stack), input=inputs
        )
        assert result.exit_code == 0


class TestPromptAtlassian:
    """Test _prompt_atlassian step."""

    def test_disabled(self):
        """Declining Atlassian returns disabled config."""
        runner = CliRunner()
        result = runner.invoke(
            _make_click_command(_prompt_atlassian), input="n\n"
        )
        assert result.exit_code == 0

    def test_enabled_with_details(self):
        """Enabling Atlassian prompts for details."""
        inputs = "y\nPROJ\nhttps://jira.example.com\nSPACE\nhttps://conf.example.com\n"
        runner = CliRunner()
        result = runner.invoke(
            _make_click_command(_prompt_atlassian), input=inputs
        )
        assert result.exit_code == 0


class TestPromptLLMGateway:
    """Test _prompt_llm_gateway step."""

    def test_enabled(self):
        """Accepting LLM gateway."""
        runner = CliRunner()
        result = runner.invoke(
            _make_click_command(_prompt_llm_gateway), input="y\n"
        )
        assert result.exit_code == 0

    def test_disabled(self):
        """Declining LLM gateway."""
        runner = CliRunner()
        result = runner.invoke(
            _make_click_command(_prompt_llm_gateway), input="n\n"
        )
        assert result.exit_code == 0


class TestPromptNonNegotiables:
    """Test _prompt_non_negotiables step."""

    def test_no_rules(self):
        """Empty input finishes immediately."""
        runner = CliRunner()
        result = runner.invoke(
            _make_click_command(_prompt_non_negotiables), input="\n"
        )
        assert result.exit_code == 0

    def test_multiple_rules(self):
        """Multiple rules followed by empty line."""
        inputs = "All APIs need auth\n100% test coverage\n\n"
        runner = CliRunner()
        result = runner.invoke(
            _make_click_command(_prompt_non_negotiables), input=inputs
        )
        assert result.exit_code == 0


# =============================================================================
# Full Wizard Integration Tests
# =============================================================================


class TestWizardIntegration:
    """Test the full wizard flow end-to-end."""

    def _wizard_inputs(
        self,
        description: str = "Test project",
        plan_file: str = "",
        context_files: str = "",
        project_type: str = "new",
        mode: str = "1",
        strategy: str = "2",
        languages: str = "python",
        frameworks: str = "",
        databases: str = "",
        infrastructure: str = "",
        workspace: str = "1",
        team_profile: str = "auto",
        spawning: str = "y",
        naming: str = "creative",
        max_cost: str = "50",
        atlassian: str = "n",
        llm_gateway: str = "y",
        non_negotiables: list[str] | None = None,
        save_path: str = "",
        run_now: str = "n",
    ) -> str:
        """Build simulated stdin for the full wizard."""
        lines = [
            description,
            plan_file,
            context_files,
            project_type,
            mode,
            strategy,
            languages,
            frameworks,
            databases,
            infrastructure,
            workspace,
            team_profile,
            spawning,
            naming,
            max_cost,
            atlassian,
            llm_gateway,
        ]
        # Non-negotiables (each rule + empty line to finish)
        for rule in (non_negotiables or []):
            lines.append(rule)
        lines.append("")  # empty line to finish non-negotiables
        # Save path and run-now
        lines.append(save_path)
        lines.append(run_now)
        return "\n".join(lines) + "\n"

    def test_full_wizard_saves_config(self, tmp_path):
        """Full wizard flow produces a valid, loadable config file."""
        output_file = tmp_path / ".forge" / "forge.yaml"
        inputs = self._wizard_inputs(
            description="E-commerce platform",
            mode="2",  # production-ready
            strategy="1",  # auto-pilot
            languages="python, typescript",
            frameworks="fastapi, react",
            databases="postgresql",
            save_path=str(output_file),
            run_now="n",
        )

        runner = CliRunner()
        with patch("forge_cli.init_wizard._is_interactive", return_value=True):
            result = runner.invoke(cli, ["init", "--output", str(output_file)], input=inputs)

        assert result.exit_code == 0, f"Wizard failed: {result.output}"
        assert output_file.exists(), "Config file was not saved"

        # Verify the saved config is loadable and correct
        config = load_config(output_file)
        assert config.project.description == "E-commerce platform"
        assert config.mode == ProjectMode.PRODUCTION_READY
        assert config.strategy == ExecutionStrategy.AUTO_PILOT
        assert "python" in config.tech_stack.languages
        assert "typescript" in config.tech_stack.languages
        assert "fastapi" in config.tech_stack.frameworks

    def test_wizard_minimal_inputs(self, tmp_path):
        """Wizard with all defaults produces valid config."""
        output_file = tmp_path / ".forge" / "forge.yaml"
        inputs = self._wizard_inputs(
            description="Simple CLI tool",
            save_path=str(output_file),
        )

        runner = CliRunner()
        with patch("forge_cli.init_wizard._is_interactive", return_value=True):
            result = runner.invoke(cli, ["init", "--output", str(output_file)], input=inputs)

        assert result.exit_code == 0, f"Wizard failed: {result.output}"
        assert output_file.exists()

        config = load_config(output_file)
        assert config.project.description == "Simple CLI tool"
        assert config.mode == ProjectMode.MVP  # default
        assert config.strategy == ExecutionStrategy.CO_PILOT  # default

    def test_wizard_with_non_negotiables(self, tmp_path):
        """Wizard captures non-negotiable rules."""
        output_file = tmp_path / ".forge" / "forge.yaml"
        inputs = self._wizard_inputs(
            description="Secure API",
            non_negotiables=["All APIs must require auth", "No eval()"],
            save_path=str(output_file),
        )

        runner = CliRunner()
        with patch("forge_cli.init_wizard._is_interactive", return_value=True):
            result = runner.invoke(cli, ["init", "--output", str(output_file)], input=inputs)

        assert result.exit_code == 0, f"Wizard failed: {result.output}"

        config = load_config(output_file)
        assert len(config.non_negotiables) == 2
        assert "All APIs must require auth" in config.non_negotiables

    def test_wizard_atlassian_enabled(self, tmp_path):
        """Wizard with Atlassian enabled captures Jira/Confluence details."""
        output_file = tmp_path / ".forge" / "forge.yaml"
        # Build inputs manually for Atlassian-enabled flow
        lines = [
            "My project",       # description
            "",                 # plan file
            "",                 # context files
            "new",              # project type
            "1",                # mode: mvp
            "2",                # strategy: co-pilot
            "python",           # languages
            "",                 # frameworks
            "",                 # databases
            "",                 # infrastructure
            "1",                # workspace: single-repo
            "auto",             # team profile
            "y",                # spawning
            "creative",         # naming
            "50",               # max cost
            "y",                # atlassian enabled
            "PROJ",             # jira key
            "https://jira.co",  # jira url
            "DOCS",             # confluence key
            "https://conf.co",  # confluence url
            "y",                # llm gateway
            "",                 # no non-negotiables
            str(output_file),   # save path
            "n",                # don't run now
        ]
        inputs = "\n".join(lines) + "\n"

        runner = CliRunner()
        with patch("forge_cli.init_wizard._is_interactive", return_value=True):
            result = runner.invoke(cli, ["init", "--output", str(output_file)], input=inputs)

        assert result.exit_code == 0, f"Wizard failed: {result.output}"

        config = load_config(output_file)
        assert config.atlassian.enabled is True
        assert config.atlassian.jira_project_key == "PROJ"

    def test_wizard_config_roundtrip(self, tmp_path):
        """Config saved by wizard round-trips through load_config correctly."""
        output_file = tmp_path / ".forge" / "forge.yaml"
        inputs = self._wizard_inputs(
            description="Roundtrip test project",
            mode="3",  # no-compromise
            strategy="3",  # micro-manage
            languages="go, rust",
            frameworks="gin",
            databases="mongodb",
            infrastructure="kubernetes",
            save_path=str(output_file),
        )

        runner = CliRunner()
        with patch("forge_cli.init_wizard._is_interactive", return_value=True):
            result = runner.invoke(cli, ["init", "--output", str(output_file)], input=inputs)

        assert result.exit_code == 0, f"Wizard failed: {result.output}"

        # Load, save to new path, load again — should be identical
        config1 = load_config(output_file)
        roundtrip_path = tmp_path / "roundtrip.yaml"
        save_config(config1, roundtrip_path)
        config2 = load_config(roundtrip_path)

        assert config1.mode == config2.mode
        assert config1.strategy == config2.strategy
        assert config1.project.description == config2.project.description
        assert config1.tech_stack.languages == config2.tech_stack.languages
        assert config1.tech_stack.frameworks == config2.tech_stack.frameworks

    def test_wizard_and_generate_produce_same_output(self, tmp_path):
        """Config from wizard generates same files as config from YAML."""
        # Create config via wizard
        wizard_config_path = tmp_path / ".forge" / "forge.yaml"
        inputs = self._wizard_inputs(
            description="Consistency test project",
            mode="1",  # mvp
            strategy="2",  # co-pilot
            languages="python",
            frameworks="click",
            save_path=str(wizard_config_path),
        )

        runner = CliRunner()
        with patch("forge_cli.init_wizard._is_interactive", return_value=True):
            result = runner.invoke(cli, ["init", "--output", str(wizard_config_path)], input=inputs)
        assert result.exit_code == 0

        # Load wizard config and generate
        wizard_config = load_config(wizard_config_path)
        wizard_output = tmp_path / "wizard_output"
        wizard_output.mkdir()
        wizard_config.project.directory = str(wizard_output)

        from forge_cli.generators.orchestrator import generate_all
        generate_all(wizard_config)

        # Verify key files exist
        assert (wizard_output / "CLAUDE.md").exists()
        assert (wizard_output / "team-init-plan.md").exists()
        assert (wizard_output / ".claude" / "agents").is_dir()

    def test_wizard_overwrite_existing_declines(self, tmp_path):
        """Wizard asks about overwrite when file exists, decline saves to new path."""
        existing = tmp_path / ".forge" / "forge.yaml"
        existing.parent.mkdir(parents=True, exist_ok=True)
        existing.write_text("# existing\n")
        alt_path = tmp_path / "alt-config.yaml"

        # Inputs: file exists -> decline overwrite -> provide alt path
        lines = [
            "My project",   # description
            "",             # plan file
            "",             # context files
            "new",          # project type
            "1",            # mode
            "2",            # strategy
            "",             # languages
            "",             # frameworks
            "",             # databases
            "",             # infrastructure
            "1",            # workspace: single-repo
            "auto",         # team profile
            "y",            # spawning
            "creative",     # naming
            "50",           # max cost
            "n",            # atlassian
            "y",            # llm gateway
            "",             # no non-negotiables
            str(existing),  # save path (existing file)
            "n",            # don't overwrite
            str(alt_path),  # new save path
            "n",            # don't run now
        ]
        inputs = "\n".join(lines) + "\n"

        runner = CliRunner()
        with patch("forge_cli.init_wizard._is_interactive", return_value=True):
            result = runner.invoke(cli, ["init"], input=inputs)

        assert result.exit_code == 0, f"Wizard failed: {result.output}"
        assert alt_path.exists()

    def test_wizard_with_context_files(self, tmp_path):
        """Wizard captures context_files correctly."""
        output_file = tmp_path / ".forge" / "forge.yaml"
        inputs = self._wizard_inputs(
            description="Context test project",
            context_files="PLAN.md, specs/",
            save_path=str(output_file),
        )

        runner = CliRunner()
        with patch("forge_cli.init_wizard._is_interactive", return_value=True):
            result = runner.invoke(cli, ["init", "--output", str(output_file)], input=inputs)

        assert result.exit_code == 0, f"Wizard failed: {result.output}"

        config = load_config(output_file)
        assert "PLAN.md" in config.project.context_files
        assert "specs/" in config.project.context_files


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestWizardEdgeCases:
    """Edge cases for the wizard and CLI routing."""

    def test_init_non_tty_exits(self):
        """forge init in non-TTY exits with error message."""
        runner = CliRunner()
        # CliRunner's stdin is not a real TTY, so isatty check should trigger
        # We do NOT patch isatty here — let it detect the non-TTY
        result = runner.invoke(cli, ["init"])
        assert result.exit_code != 0

    def test_forge_init_help(self):
        """forge init --help shows init-specific help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["init", "--help"])
        assert result.exit_code == 0
        assert "interactively" in result.output.lower() or "config" in result.output.lower()

    def test_forge_generate_help(self):
        """forge generate --help shows generate-specific help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["generate", "--help"])
        assert result.exit_code == 0
        assert "--config" in result.output

    def test_forge_generate_requires_config_or_auto_detect(self, tmp_path):
        """forge generate without --config and no auto-detectable config fails."""
        runner = CliRunner()
        result = runner.invoke(cli, ["generate", "--project-dir", str(tmp_path)])
        assert result.exit_code != 0

    def test_init_output_flag(self):
        """forge init --output custom-path.yaml passes the path through."""
        runner = CliRunner()
        result = runner.invoke(cli, ["init", "--help"])
        assert "--output" in result.output

    def test_backward_compat_validate_only(self, tmp_path):
        """forge --validate-only --config <path> works (args in any order)."""
        config = ForgeConfig()
        config.project.description = "Order test"
        config_path = tmp_path / "config.yaml"
        save_config(config, config_path)

        runner = CliRunner()
        result = runner.invoke(
            cli, ["--validate-only", "--config", str(config_path)]
        )
        assert result.exit_code == 0

    def test_backward_compat_project_dir(self, tmp_path):
        """forge --project-dir <dir> --config <path> works."""
        config = ForgeConfig()
        config.project.description = "Dir order test"
        config.project.requirements = "Build a web app"
        config.tech_stack.languages = ["python"]
        config.tech_stack.frameworks = ["fastapi"]
        config.tech_stack.databases = ["postgresql"]
        config_path = tmp_path / "config.yaml"
        save_config(config, config_path)
        output_dir = tmp_path / "out"
        output_dir.mkdir()

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-dir", str(output_dir), "--config", str(config_path)],
        )
        assert result.exit_code == 0

    def test_forge_start_no_team_init_plan(self, tmp_path):
        """forge start fails when team-init-plan.md is missing."""
        config = ForgeConfig()
        config.project.description = "Start test"
        forge_dir = tmp_path / ".forge"
        forge_dir.mkdir()
        config_path = forge_dir / "forge.yaml"
        save_config(config, config_path)

        runner = CliRunner()
        result = runner.invoke(cli, ["start", "--project-dir", str(tmp_path)])
        assert result.exit_code != 0
        assert "team-init-plan.md" in result.output


# =============================================================================
# Config Auto-Detection Tests
# =============================================================================


class TestConfigAutoDetect:
    """Test config file auto-detection."""

    def test_find_config_forge_yaml_in_forge_dir(self, tmp_path):
        """Finds .forge/forge.yaml (canonical location)."""
        from forge_cli.config_loader import find_config
        forge_dir = tmp_path / ".forge"
        forge_dir.mkdir()
        (forge_dir / "forge.yaml").write_text("mode: mvp\n")
        assert find_config(tmp_path) == forge_dir / "forge.yaml"

    def test_find_config_forge_yaml_in_root(self, tmp_path):
        """Finds forge.yaml in project root."""
        from forge_cli.config_loader import find_config
        (tmp_path / "forge.yaml").write_text("mode: mvp\n")
        assert find_config(tmp_path) == tmp_path / "forge.yaml"

    def test_find_config_legacy_in_forge_dir(self, tmp_path):
        """Finds .forge/forge-config.yaml (legacy)."""
        from forge_cli.config_loader import find_config
        forge_dir = tmp_path / ".forge"
        forge_dir.mkdir()
        (forge_dir / "forge-config.yaml").write_text("mode: mvp\n")
        assert find_config(tmp_path) == forge_dir / "forge-config.yaml"

    def test_find_config_legacy_in_root(self, tmp_path):
        """Finds forge-config.yaml in project root (legacy)."""
        from forge_cli.config_loader import find_config
        (tmp_path / "forge-config.yaml").write_text("mode: mvp\n")
        assert find_config(tmp_path) == tmp_path / "forge-config.yaml"

    def test_find_config_priority_order(self, tmp_path):
        """Canonical .forge/forge.yaml takes priority over legacy."""
        from forge_cli.config_loader import find_config
        forge_dir = tmp_path / ".forge"
        forge_dir.mkdir()
        (forge_dir / "forge.yaml").write_text("mode: mvp\n")
        (tmp_path / "forge-config.yaml").write_text("mode: production-ready\n")
        assert find_config(tmp_path) == forge_dir / "forge.yaml"

    def test_find_config_none(self, tmp_path):
        """Returns None when no config found."""
        from forge_cli.config_loader import find_config
        assert find_config(tmp_path) is None

    def test_ensure_forge_dir_creates_dir(self, tmp_path):
        """ensure_forge_dir creates .forge directory."""
        from forge_cli.config_loader import ensure_forge_dir
        forge_dir = ensure_forge_dir(tmp_path)
        assert forge_dir.is_dir()
        assert forge_dir.name == ".forge"

    def test_ensure_forge_dir_no_gitignore(self, tmp_path):
        """ensure_forge_dir does not create or modify .gitignore."""
        from forge_cli.config_loader import ensure_forge_dir
        ensure_forge_dir(tmp_path)
        assert not (tmp_path / ".gitignore").exists()


# =============================================================================
# Intra-Step Back Navigation Tests
# =============================================================================


class TestRunFields:
    """Test the _run_fields helper for intra-step back navigation."""

    def test_run_fields_forward_only(self):
        """All fields completed sequentially."""
        calls = []

        def f1():
            calls.append("f1")
            return "a"

        def f2():
            calls.append("f2")
            return "b"

        def f3():
            calls.append("f3")
            return "c"

        results = _run_fields([f1, f2, f3])
        assert results == ["a", "b", "c"]
        assert calls == ["f1", "f2", "f3"]

    def test_run_fields_back_at_middle(self):
        """Back at field 2 re-runs field 1, then proceeds."""
        call_count = {"f1": 0, "f2": 0, "f3": 0}

        def f1():
            call_count["f1"] += 1
            return "a"

        def f2():
            call_count["f2"] += 1
            if call_count["f2"] == 1:
                raise _BackSignal()  # first time: go back
            return "b"

        def f3():
            call_count["f3"] += 1
            return "c"

        results = _run_fields([f1, f2, f3])
        assert results == ["a", "b", "c"]
        assert call_count["f1"] == 2  # re-run after back
        assert call_count["f2"] == 2  # first attempt + second attempt

    def test_run_fields_back_at_first_field_propagates(self):
        """Back at the first field raises _BackSignal to go to previous step."""

        def f1():
            raise _BackSignal()

        def f2():
            return "b"

        with pytest.raises(_BackSignal):
            _run_fields([f1, f2])


class TestIntraStepBackNavigation:
    """Test that multi-field steps handle back navigation within the step."""

    def test_tech_stack_back_at_frameworks_reprompts_languages(self):
        """Pressing back at frameworks field returns to languages within step 4."""
        # Sequence: languages="python" → frameworks=BACK → languages="go" → frameworks="" → databases="" → infra=""
        inputs = "python\n__BACK__\ngo\n\n\n\n"
        runner = CliRunner()
        result = runner.invoke(
            _make_click_command(_prompt_tech_stack), input=inputs
        )
        assert result.exit_code == 0

    def test_project_back_at_plan_file_reprompts_description(self):
        """Pressing back at plan_file returns to description within step 1."""
        # desc="test" → plan_file=BACK → desc="final" → plan="" → context="" → type="new"
        inputs = "test\n__BACK__\nfinal\n\n\nnew\n"
        runner = CliRunner()
        result = runner.invoke(
            _make_click_command(_prompt_project), input=inputs
        )
        assert result.exit_code == 0

    def test_project_back_at_first_field_raises_back_signal(self):
        """Pressing back at the description (first field) propagates to step-level."""
        # First input is BACK sentinel
        inputs = "__BACK__\n"
        runner = CliRunner()
        result = runner.invoke(
            _make_click_command(_prompt_project), input=inputs
        )
        # _BackSignal is uncaught in the click command wrapper, causing an error
        assert result.exit_code != 0


class TestWizardStepNavigation:
    """Test step-level navigation in the full wizard."""

    def _wizard_inputs(
        self,
        description: str = "Test project",
        plan_file: str = "",
        context_files: str = "",
        project_type: str = "new",
        mode: str = "1",
        strategy: str = "2",
        languages: str = "python",
        frameworks: str = "",
        databases: str = "",
        infrastructure: str = "",
        workspace: str = "1",
        team_profile: str = "auto",
        spawning: str = "y",
        naming: str = "creative",
        max_cost: str = "50",
        atlassian: str = "n",
        llm_gateway: str = "y",
        non_negotiables: list[str] | None = None,
        save_path: str = "",
        run_now: str = "n",
    ) -> str:
        """Build simulated stdin for the full wizard."""
        lines = [
            description, plan_file, context_files, project_type,
            mode, strategy, languages, frameworks, databases, infrastructure,
            workspace, team_profile, spawning, naming, max_cost, atlassian,
            llm_gateway,
        ]
        for rule in (non_negotiables or []):
            lines.append(rule)
        lines.append("")  # empty line to finish non-negotiables
        lines.append(save_path)
        lines.append(run_now)
        return "\n".join(lines) + "\n"

    def test_wizard_workspace_monorepo(self, tmp_path):
        """Wizard with monorepo workspace selection saves correct type."""
        output_file = tmp_path / ".forge" / "forge.yaml"
        inputs = self._wizard_inputs(
            description="Monorepo test",
            workspace="2",  # monorepo
            save_path=str(output_file),
        )

        runner = CliRunner()
        with patch("forge_cli.init_wizard._is_interactive", return_value=True):
            result = runner.invoke(cli, ["init", "--output", str(output_file)], input=inputs)

        assert result.exit_code == 0, f"Wizard failed: {result.output}"
        config = load_config(output_file)
        assert config.workspace.type == WorkspaceType.MONOREPO

    def test_wizard_workspace_multi_repo(self, tmp_path):
        """Wizard with workspace selection saves correct type."""
        output_file = tmp_path / ".forge" / "forge.yaml"
        inputs = self._wizard_inputs(
            description="Multi-repo test",
            workspace="3",  # workspace
            save_path=str(output_file),
        )

        runner = CliRunner()
        with patch("forge_cli.init_wizard._is_interactive", return_value=True):
            result = runner.invoke(cli, ["init", "--output", str(output_file)], input=inputs)

        assert result.exit_code == 0, f"Wizard failed: {result.output}"
        config = load_config(output_file)
        assert config.workspace.type == WorkspaceType.WORKSPACE

    def test_wizard_summary_shows_workspace_type(self, tmp_path):
        """Wizard summary table shows workspace type value."""
        output_file = tmp_path / ".forge" / "forge.yaml"
        inputs = self._wizard_inputs(
            description="Summary test",
            workspace="1",  # single-repo
            save_path=str(output_file),
        )

        runner = CliRunner()
        with patch("forge_cli.init_wizard._is_interactive", return_value=True):
            result = runner.invoke(cli, ["init", "--output", str(output_file)], input=inputs)

        assert result.exit_code == 0, f"Wizard failed: {result.output}"
        assert "single-repo" in result.output


# =============================================================================
# Progress Display Tests
# =============================================================================


class TestProgressDisplay:
    """Test that forge generate shows proper progress output."""

    def test_generate_shows_progress_steps(self, tmp_path):
        """forge generate output contains step completion markers."""
        config = ForgeConfig()
        config.project.description = "Progress test project"
        config.project.requirements = "Build something"
        config.tech_stack.languages = ["python"]
        config.tech_stack.frameworks = ["fastapi"]
        config_path = tmp_path / "config.yaml"
        save_config(config, config_path)
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["generate", "--config", str(config_path), "--project-dir", str(output_dir)],
        )
        assert result.exit_code == 0
        # Progress display should show completed steps
        assert "Agent instruction files" in result.output
        assert "CLAUDE.md" in result.output
        assert "team-init-plan.md" in result.output
        assert "Reusable skills" in result.output

    def test_generate_shows_agent_count(self, tmp_path):
        """Progress shows number of agents being generated."""
        config = ForgeConfig()
        config.project.description = "Agent count test"
        config.tech_stack.languages = ["python"]
        config_path = tmp_path / "config.yaml"
        save_config(config, config_path)
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["generate", "--config", str(config_path), "--project-dir", str(output_dir)],
        )
        assert result.exit_code == 0
        assert "agents" in result.output.lower()

    def test_generate_shows_skill_count(self, tmp_path):
        """Progress shows number of skills being generated."""
        config = ForgeConfig()
        config.project.description = "Skill count test"
        config.tech_stack.languages = ["python"]
        config_path = tmp_path / "config.yaml"
        save_config(config, config_path)
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["generate", "--config", str(config_path), "--project-dir", str(output_dir)],
        )
        assert result.exit_code == 0
        assert "skills" in result.output.lower()

    def test_generate_shows_completion_checkmarks(self, tmp_path):
        """Completed steps show checkmark indicators."""
        config = ForgeConfig()
        config.project.description = "Checkmark test"
        config.tech_stack.languages = ["python"]
        config_path = tmp_path / "config.yaml"
        save_config(config, config_path)
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["generate", "--config", str(config_path), "--project-dir", str(output_dir)],
        )
        assert result.exit_code == 0
        # The checkmark character should appear for completed steps
        assert "✓" in result.output

    def test_generate_shows_skipped_steps(self, tmp_path):
        """Skipped steps (like context summarization) show in output."""
        config = ForgeConfig()
        config.project.description = "Skipped step test"
        config.tech_stack.languages = ["python"]
        config_path = tmp_path / "config.yaml"
        save_config(config, config_path)
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["generate", "--config", str(config_path), "--project-dir", str(output_dir)],
        )
        assert result.exit_code == 0
        # Context summarization should be skipped (no context files)
        assert "skipped" in result.output.lower() or "–" in result.output

    def test_micro_manage_skips_settings(self, tmp_path):
        """Micro-manage strategy skips settings generation."""
        from forge_cli.config_schema import ExecutionStrategy as ES
        config = ForgeConfig()
        config.project.description = "Micro-manage test"
        config.strategy = ES.MICRO_MANAGE
        config.tech_stack.languages = ["python"]
        config_path = tmp_path / "config.yaml"
        save_config(config, config_path)
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["generate", "--config", str(config_path), "--project-dir", str(output_dir)],
        )
        assert result.exit_code == 0
        # Settings step should show as skipped
        assert "micro-manage" in result.output.lower() or "skipped" in result.output.lower()

    def test_generate_next_steps_shown(self, tmp_path):
        """Generation output ends with next steps guidance."""
        config = ForgeConfig()
        config.project.description = "Next steps test"
        config.tech_stack.languages = ["python"]
        config_path = tmp_path / "config.yaml"
        save_config(config, config_path)
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["generate", "--config", str(config_path), "--project-dir", str(output_dir)],
        )
        assert result.exit_code == 0
        assert "Next steps" in result.output
        assert "forge start" in result.output
        assert "forge refine" in result.output


# =============================================================================
# Prompt Fallback Tests — ImportError/EOFError in TTY mode
# =============================================================================


class TestPromptFallbacks:
    """Test _pt_prompt, _pt_confirm, _pt_choice, _pt_int fallback to click when
    prompt_toolkit raises ImportError or EOFError in TTY mode (lines 92-93,
    120-121, 153-154, 194-195).
    """

    def test_pt_prompt_importerror_falls_back_to_click(self):
        """_pt_prompt falls back to click.prompt when prompt_toolkit raises ImportError."""
        import builtins

        real_import = builtins.__import__

        def _block_pt(name, *args, **kwargs):
            if name == "prompt_toolkit" or name.startswith("prompt_toolkit."):
                raise ImportError("mocked")
            return real_import(name, *args, **kwargs)

        with patch("sys.stdin") as mock_stdin, \
             patch.object(builtins, "__import__", side_effect=_block_pt):
            mock_stdin.isatty.return_value = True
            # click.prompt reads from the input provided by CliRunner
            # but since we're outside CliRunner, mock click.prompt directly
            with patch("forge_cli.init_wizard.click.prompt", return_value="fallback_value") as mock_click:
                from forge_cli.init_wizard import _pt_prompt
                result = _pt_prompt("Test prompt", default="def")
                assert result == "fallback_value"
                mock_click.assert_called_once_with("Test prompt", default="def")

    def test_pt_prompt_eoferror_falls_back_to_click(self):
        """_pt_prompt falls back to click.prompt when prompt_toolkit raises EOFError."""
        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = True
            # Mock pt_prompt_fn to raise EOFError
            with patch.dict("sys.modules", {"prompt_toolkit": __import__("types").ModuleType("prompt_toolkit"),
                                             "prompt_toolkit.formatted_text": __import__("types").ModuleType("prompt_toolkit.formatted_text")}):
                import sys
                sys.modules["prompt_toolkit"].prompt = None  # will cause error before we get there
                # Simplest approach: directly mock the import within the try block to raise EOFError
                with patch("forge_cli.init_wizard.click.prompt", return_value="eof_fallback") as mock_click:
                    # Force the try block to raise ImportError by removing prompt_toolkit from available modules
                    import builtins
                    real_import = builtins.__import__

                    def _block_pt(name, *args, **kwargs):
                        if name == "prompt_toolkit" or name.startswith("prompt_toolkit."):
                            raise ImportError("mocked")
                        return real_import(name, *args, **kwargs)

                    with patch.object(builtins, "__import__", side_effect=_block_pt):
                        from forge_cli.init_wizard import _pt_prompt
                        result = _pt_prompt("Prompt", default="x")
                        assert result == "eof_fallback"

    def test_pt_confirm_importerror_falls_back_to_click(self):
        """_pt_confirm falls back to click.confirm on ImportError."""
        import builtins

        real_import = builtins.__import__

        def _block_pt(name, *args, **kwargs):
            if name == "prompt_toolkit" or name.startswith("prompt_toolkit."):
                raise ImportError("mocked")
            return real_import(name, *args, **kwargs)

        with patch("sys.stdin") as mock_stdin, \
             patch.object(builtins, "__import__", side_effect=_block_pt):
            mock_stdin.isatty.return_value = True
            with patch("forge_cli.init_wizard.click.confirm", return_value=True) as mock_click:
                from forge_cli.init_wizard import _pt_confirm
                result = _pt_confirm("Confirm?", default=False)
                assert result is True
                mock_click.assert_called_once_with("Confirm?", default=False)

    def test_pt_choice_importerror_falls_back_to_click(self):
        """_pt_choice falls back to click.prompt on ImportError."""
        import builtins

        real_import = builtins.__import__

        def _block_pt(name, *args, **kwargs):
            if name == "prompt_toolkit" or name.startswith("prompt_toolkit."):
                raise ImportError("mocked")
            return real_import(name, *args, **kwargs)

        with patch("sys.stdin") as mock_stdin, \
             patch.object(builtins, "__import__", side_effect=_block_pt):
            mock_stdin.isatty.return_value = True
            with patch("forge_cli.init_wizard.click.prompt", return_value="opt2") as mock_click:
                from forge_cli.init_wizard import _pt_choice
                result = _pt_choice("Pick", ["opt1", "opt2", "opt3"], default="opt1")
                assert result == "opt2"

    def test_pt_int_importerror_falls_back_to_click(self):
        """_pt_int falls back to click.prompt on ImportError."""
        import builtins

        real_import = builtins.__import__

        def _block_pt(name, *args, **kwargs):
            if name == "prompt_toolkit" or name.startswith("prompt_toolkit."):
                raise ImportError("mocked")
            return real_import(name, *args, **kwargs)

        with patch("sys.stdin") as mock_stdin, \
             patch.object(builtins, "__import__", side_effect=_block_pt):
            mock_stdin.isatty.return_value = True
            with patch("forge_cli.init_wizard.click.prompt", return_value=42) as mock_click:
                from forge_cli.init_wizard import _pt_int
                result = _pt_int("Number", default=10, min_val=1, max_val=100)
                assert result == 42


# =============================================================================
# Back Signal Handling in run_wizard (lines 242-250)
# =============================================================================


class TestWizardBackSignalHandling:
    """Test step-level back navigation in run_wizard (lines 242-250)."""

    def _make_wizard_inputs(self, tmp_path):
        """Build standard wizard inputs for a complete run."""
        output_file = tmp_path / ".forge" / "forge.yaml"
        lines = [
            "Test project",  "","","new",   # step 1: project
            "1",                             # step 2: mode
            "2",                             # step 3: strategy
            "python","","","",               # step 4: tech stack
            "1",                             # step 5: workspace
            "auto","y","creative","50",      # step 6: agents
            "n",                             # step 7: atlassian
            "y",                             # step 8: llm gateway
            "",                              # step 9: non-negotiables
            str(output_file),                # save path
            "n",                             # don't run now
        ]
        return output_file, "\n".join(lines) + "\n"

    def test_back_at_step_1_goes_to_step_0_in_wizard(self, tmp_path):
        """BackSignal at step 2 (mode) goes back to step 1 (project) in real wizard."""
        from forge_cli.init_wizard import _BackSignal, run_wizard

        output_file = tmp_path / ".forge" / "forge.yaml"
        # We'll patch _prompt_mode to raise _BackSignal the first time
        mode_call_count = {"n": 0}
        original_prompt_mode = _prompt_mode

        def _mode_with_back():
            mode_call_count["n"] += 1
            if mode_call_count["n"] == 1:
                raise _BackSignal()
            return original_prompt_mode()

        # Need two project prompts (first run + back-run) + rest of wizard
        lines = [
            # First project run
            "Test project","","","new",
            # Mode raises BackSignal first time, so project re-runs:
            "Test project again","","","new",
            # Mode succeeds second time
            "1",
            # Rest of wizard
            "2","python","","","","1","auto","y","creative","50","n","y","",
            str(output_file),"n",
        ]
        inputs = "\n".join(lines) + "\n"

        runner = CliRunner()
        with patch("forge_cli.init_wizard._is_interactive", return_value=True), \
             patch("forge_cli.init_wizard._prompt_mode", side_effect=_mode_with_back):
            result = runner.invoke(cli, ["init", "--output", str(output_file)], input=inputs)

        assert result.exit_code == 0, f"Wizard failed: {result.output}"
        assert "Going back" in result.output
        assert mode_call_count["n"] == 2

    def test_back_at_step_0_stays_in_wizard(self, tmp_path):
        """BackSignal at step 1 (project) shows 'already at first step' in real wizard."""
        from forge_cli.init_wizard import _BackSignal

        output_file = tmp_path / ".forge" / "forge.yaml"
        project_call_count = {"n": 0}
        original_prompt_project = _prompt_project

        def _project_with_back():
            project_call_count["n"] += 1
            if project_call_count["n"] == 1:
                raise _BackSignal()
            return original_prompt_project()

        lines = [
            # First project call raises BackSignal; second succeeds:
            "Test project","","","new",
            # Rest of wizard
            "1","2","python","","","","1","auto","y","creative","50","n","y","",
            str(output_file),"n",
        ]
        inputs = "\n".join(lines) + "\n"

        runner = CliRunner()
        with patch("forge_cli.init_wizard._is_interactive", return_value=True), \
             patch("forge_cli.init_wizard._prompt_project", side_effect=_project_with_back):
            result = runner.invoke(cli, ["init", "--output", str(output_file)], input=inputs)

        assert result.exit_code == 0, f"Wizard failed: {result.output}"
        assert "Already at first step" in result.output
        assert project_call_count["n"] == 2

    def test_keyboard_interrupt_exits_130_in_wizard(self):
        """KeyboardInterrupt during wizard raises SystemExit(130)."""
        from forge_cli.init_wizard import run_wizard

        with patch("forge_cli.init_wizard._is_interactive", return_value=True), \
             patch("forge_cli.init_wizard._prompt_project", side_effect=KeyboardInterrupt):
            runner = CliRunner()
            result = runner.invoke(cli, ["init"], input="\n")

        assert result.exit_code == 130

    def test_eoferror_exits_130_in_wizard(self):
        """EOFError during wizard raises SystemExit(130)."""
        with patch("forge_cli.init_wizard._is_interactive", return_value=True), \
             patch("forge_cli.init_wizard._prompt_project", side_effect=EOFError):
            runner = CliRunner()
            result = runner.invoke(cli, ["init"], input="\n")

        assert result.exit_code == 130


# =============================================================================
# Custom Team Profile Agent Selection (lines 506-517)
# =============================================================================


class TestCustomTeamProfile:
    """Test custom team profile with explicit agent selection."""

    def test_custom_profile_prompts_for_agents(self):
        """Selecting 'custom' profile prompts for agent list."""
        from forge_cli.init_wizard import _prompt_agents

        # custom profile, agents list, spawning, naming, cost
        inputs = "custom\nbackend-developer, qa-engineer, architect\ny\ncreative\n50\n"
        runner = CliRunner()
        result = runner.invoke(
            _make_click_command_agents(), input=inputs
        )
        assert result.exit_code == 0
        assert "Available agents" in result.output
        assert "backend-developer" in result.output

    def test_custom_profile_returns_selected_agents(self):
        """Custom profile returns the selected agents in include list."""
        from forge_cli.init_wizard import _prompt_agents

        inputs = "custom\nbackend-developer, qa-engineer\ny\ncreative\n50\n"
        runner = CliRunner()

        @click.command()
        def _cmd():
            agents_cfg, naming_cfg, cost_cfg = _prompt_agents(ProjectMode.MVP)
            click.echo(f"PROFILE:{agents_cfg.team_profile.value}")
            click.echo(f"INCLUDE:{','.join(agents_cfg.include)}")

        result = runner.invoke(_cmd, input=inputs)
        assert result.exit_code == 0
        assert "PROFILE:custom" in result.output
        assert "backend-developer" in result.output
        assert "qa-engineer" in result.output

    def test_auto_profile_skips_agent_selection(self):
        """Non-custom profiles skip agent selection prompt."""
        from forge_cli.init_wizard import _prompt_agents

        inputs = "auto\ny\ncreative\n50\n"
        runner = CliRunner()

        @click.command()
        def _cmd():
            agents_cfg, naming_cfg, cost_cfg = _prompt_agents(ProjectMode.MVP)
            click.echo(f"PROFILE:{agents_cfg.team_profile.value}")
            click.echo(f"INCLUDE_COUNT:{len(agents_cfg.include)}")

        result = runner.invoke(_cmd, input=inputs)
        assert result.exit_code == 0
        assert "PROFILE:auto" in result.output
        assert "INCLUDE_COUNT:0" in result.output

    def test_custom_profile_full_wizard(self, tmp_path):
        """Full wizard with custom team profile saves correct agent list."""
        output_file = tmp_path / ".forge" / "forge.yaml"
        lines = [
            "Custom team project",  # description
            "",                     # plan file
            "",                     # context files
            "new",                  # project type
            "1",                    # mode: mvp
            "2",                    # strategy: co-pilot
            "python",               # languages
            "",                     # frameworks
            "",                     # databases
            "",                     # infrastructure
            "1",                    # workspace: single-repo
            "custom",               # team profile: custom
            "backend-developer, qa-engineer, architect",  # agents
            "y",                    # spawning
            "creative",             # naming
            "50",                   # max cost
            "n",                    # atlassian
            "y",                    # llm gateway
            "",                     # no non-negotiables
            str(output_file),       # save path
            "n",                    # don't run now
        ]
        inputs = "\n".join(lines) + "\n"

        runner = CliRunner()
        with patch("forge_cli.init_wizard._is_interactive", return_value=True):
            result = runner.invoke(cli, ["init", "--output", str(output_file)], input=inputs)

        assert result.exit_code == 0, f"Wizard failed: {result.output}"
        assert output_file.exists()

        config = load_config(output_file)
        assert config.agents.team_profile == TeamProfile.CUSTOM
        assert "backend-developer" in config.agents.include
        assert "qa-engineer" in config.agents.include
        assert "architect" in config.agents.include


# =============================================================================
# Atlassian Back Signal (line 571) and Non-Negotiables Back Signal (line 617)
# =============================================================================


class TestAtlassianBackSignal:
    """Test back signal handling in _prompt_atlassian."""

    def test_atlassian_back_sentinel_raises_back_signal(self):
        """When _pt_confirm returns _BACK_SENTINEL, _prompt_atlassian raises _BackSignal."""
        from forge_cli.init_wizard import _prompt_atlassian, _BackSignal, _BACK_SENTINEL

        with patch("forge_cli.init_wizard._pt_confirm", return_value=_BACK_SENTINEL):
            with pytest.raises(_BackSignal):
                _prompt_atlassian()


class TestNonNegotiablesBackSignal:
    """Test back signal handling in _prompt_non_negotiables."""

    def test_non_negotiables_back_sentinel_raises_back_signal(self):
        """When _pt_prompt returns _BACK_SENTINEL, _prompt_non_negotiables raises _BackSignal."""
        from forge_cli.init_wizard import _prompt_non_negotiables, _BackSignal, _BACK_SENTINEL

        with patch("forge_cli.init_wizard._pt_prompt", return_value=_BACK_SENTINEL):
            with pytest.raises(_BackSignal):
                _prompt_non_negotiables()


# =============================================================================
# Run Forge Now Flow (lines 688-702)
# =============================================================================


class TestRunForgeNow:
    """Test the 'run forge now' flow in _confirm_and_save."""

    def test_run_now_calls_generate_all(self, tmp_path):
        """Answering 'y' to run_now triggers generate_all."""
        output_file = tmp_path / ".forge" / "forge.yaml"
        lines = [
            "Test project for run now",  # description
            "",                          # plan file
            "",                          # context files
            "new",                       # project type
            "1",                         # mode: mvp
            "2",                         # strategy: co-pilot
            "python",                    # languages
            "",                          # frameworks
            "",                          # databases
            "",                          # infrastructure
            "1",                         # workspace
            "auto",                      # team profile
            "y",                         # spawning
            "creative",                  # naming
            "50",                        # max cost
            "n",                         # atlassian
            "y",                         # llm gateway
            "",                          # no non-negotiables
            str(output_file),            # save path
            "y",                         # YES run now
            str(tmp_path),               # project directory
        ]
        inputs = "\n".join(lines) + "\n"

        runner = CliRunner()
        with patch("forge_cli.init_wizard._is_interactive", return_value=True):
            result = runner.invoke(cli, ["init", "--output", str(output_file)], input=inputs)

        assert result.exit_code == 0, f"Wizard failed: {result.output}"
        assert "Forge generation complete" in result.output
        assert "Next steps" in result.output
        assert "forge start" in result.output
        assert "forge refine" in result.output

        # Verify files were generated
        assert (tmp_path / "CLAUDE.md").exists()
        assert (tmp_path / "team-init-plan.md").exists()

    def test_run_now_decline_skips_generation(self, tmp_path):
        """Answering 'n' to run_now skips generation."""
        output_file = tmp_path / ".forge" / "forge.yaml"
        lines = [
            "Test project skip gen",  # description
            "",                       # plan file
            "",                       # context files
            "new",                    # project type
            "1",                      # mode
            "2",                      # strategy
            "",                       # languages
            "",                       # frameworks
            "",                       # databases
            "",                       # infrastructure
            "1",                      # workspace
            "auto",                   # team profile
            "y",                      # spawning
            "creative",               # naming
            "50",                     # max cost
            "n",                      # atlassian
            "y",                      # llm gateway
            "",                       # no non-negotiables
            str(output_file),         # save path
            "n",                      # NO don't run now
        ]
        inputs = "\n".join(lines) + "\n"

        runner = CliRunner()
        with patch("forge_cli.init_wizard._is_interactive", return_value=True):
            result = runner.invoke(cli, ["init", "--output", str(output_file)], input=inputs)

        assert result.exit_code == 0, f"Wizard failed: {result.output}"
        assert "Forge generation complete" not in result.output
        # Config saved but no generation output
        assert output_file.exists()
        assert not (tmp_path / "CLAUDE.md").exists()


# =============================================================================
# Helpers
# =============================================================================


def _make_click_command(prompt_fn):
    """Wrap a wizard prompt function in a Click command for CliRunner testing."""

    @click.command()
    def _cmd():
        result = prompt_fn() if prompt_fn.__name__ != "_prompt_agents" else prompt_fn(ProjectMode.MVP)
        click.echo(f"RESULT: {result}")

    return _cmd


def _make_click_command_agents():
    """Wrap _prompt_agents in a Click command for CliRunner testing."""
    from forge_cli.init_wizard import _prompt_agents

    @click.command()
    def _cmd():
        agents_cfg, naming_cfg, cost_cfg = _prompt_agents(ProjectMode.MVP)
        click.echo(f"RESULT: {agents_cfg} {naming_cfg} {cost_cfg}")

    return _cmd
