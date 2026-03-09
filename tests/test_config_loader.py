"""Tests for config loading and saving."""

from pathlib import Path

import yaml

from forge_cli.config_loader import load_config, save_config
from forge_cli.config_schema import (
    AtlassianConfig,
    ForgeConfig,
    GitConfig,
    ProjectConfig,
    ProjectMode,
    RefinementConfig,
)


class TestConfigLoader:
    def test_load_config_from_yaml(self, tmp_path):
        config_data = {
            "project": {
                "description": "Test",
                "requirements": "Build stuff",
                "type": "new",
                "directory": "/tmp/test",
            },
            "mode": "production-ready",
            "strategy": "auto-pilot",
            "agents": {"team_profile": "full"},
            "atlassian": {"enabled": False},
        }
        config_file = tmp_path / "forge-config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = load_config(config_file)
        assert config.project.description == "Test"
        assert config.mode == ProjectMode.PRODUCTION_READY
        assert config.resolve_team_profile() == "full"

    def test_save_and_reload_config(self, tmp_path):
        config = ForgeConfig(
            project=ProjectConfig(description="Roundtrip Test"),
            mode=ProjectMode.NO_COMPROMISE,
            atlassian=AtlassianConfig(enabled=True, jira_project_key="RT"),
        )

        config_file = tmp_path / "forge-config.yaml"
        save_config(config, config_file)

        reloaded = load_config(config_file)
        assert reloaded.project.description == "Roundtrip Test"
        assert reloaded.mode == ProjectMode.NO_COMPROMISE
        assert reloaded.atlassian.jira_project_key == "RT"

    def test_load_missing_file_raises(self, tmp_path):
        try:
            load_config(tmp_path / "nonexistent.yaml")
            assert False, "Should have raised"
        except FileNotFoundError:
            pass

    def test_load_minimal_config(self, tmp_path):
        config_file = tmp_path / "forge-config.yaml"
        config_file.write_text("mode: mvp\n")

        config = load_config(config_file)
        assert config.mode == ProjectMode.MVP
        assert config.project.description == ""

    def test_load_config_with_non_negotiables(self, tmp_path):
        config_data = {
            "mode": "mvp",
            "non_negotiables": [
                "All APIs must be authenticated",
                "100% test coverage on core modules",
            ],
        }
        config_file = tmp_path / "forge-config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = load_config(config_file)
        assert len(config.non_negotiables) == 2
        assert "All APIs must be authenticated" in config.non_negotiables

    def test_round_trip_non_negotiables(self, tmp_path):
        config = ForgeConfig(
            project=ProjectConfig(description="Roundtrip NN"),
            non_negotiables=["No vendor lock-in", "All data encrypted at rest"],
        )

        config_file = tmp_path / "forge-config.yaml"
        save_config(config, config_file)

        reloaded = load_config(config_file)
        assert reloaded.non_negotiables == ["No vendor lock-in", "All data encrypted at rest"]

    def test_load_config_with_refinement(self, tmp_path):
        config_data = {
            "mode": "production-ready",
            "refinement": {
                "enabled": True,
                "provider": "anthropic",
                "model": "claude-sonnet-4-20250514",
                "score_threshold": 85,
                "max_iterations": 3,
            },
        }
        config_file = tmp_path / "forge-config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = load_config(config_file)
        assert config.refinement.enabled is True
        assert config.refinement.provider == "anthropic"
        assert config.refinement.score_threshold == 85
        assert config.refinement.max_iterations == 3
        # Defaults for unspecified fields
        assert config.refinement.timeout_seconds == 180
        assert config.refinement.cost_limit_usd == 10.0

    def test_round_trip_refinement(self, tmp_path):
        config = ForgeConfig(
            project=ProjectConfig(description="Roundtrip Refinement"),
            refinement=RefinementConfig(
                enabled=True,
                provider="anthropic",
                model="claude-opus-4-6",
                score_threshold=92,
                max_iterations=4,
                cost_limit_usd=7.5,
            ),
        )

        config_file = tmp_path / "forge-config.yaml"
        save_config(config, config_file)

        reloaded = load_config(config_file)
        assert reloaded.refinement.enabled is True
        assert reloaded.refinement.provider == "anthropic"
        assert reloaded.refinement.score_threshold == 92
        assert reloaded.refinement.max_iterations == 4
        assert reloaded.refinement.cost_limit_usd == 7.5

    def test_load_config_with_git_ssh(self, tmp_path):
        config_data = {
            "mode": "mvp",
            "git": {"ssh_key_path": "~/.ssh/id_ed25519"},
        }
        config_file = tmp_path / "forge-config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = load_config(config_file)
        assert config.git.ssh_key_path == "~/.ssh/id_ed25519"
        assert config.has_ssh_auth() is True

    def test_round_trip_git_config(self, tmp_path):
        config = ForgeConfig(
            project=ProjectConfig(description="Roundtrip Git"),
            git=GitConfig(ssh_key_path="~/.ssh/id_rsa"),
        )

        config_file = tmp_path / "forge-config.yaml"
        save_config(config, config_file)

        reloaded = load_config(config_file)
        assert reloaded.git.ssh_key_path == "~/.ssh/id_rsa"
