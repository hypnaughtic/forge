"""Tests for config loading and saving."""

from pathlib import Path

import yaml

from forge_cli.config_loader import load_config, save_config
from forge_cli.config_schema import (
    AtlassianConfig,
    ForgeConfig,
    ProjectConfig,
    ProjectMode,
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
