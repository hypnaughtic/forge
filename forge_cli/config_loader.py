"""Load and validate forge configuration from YAML."""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

from forge_cli.config_schema import ForgeConfig

logger = logging.getLogger(__name__)

# Default config filename and search locations
CONFIG_FILENAME = "forge.yaml"
LEGACY_CONFIG_FILENAME = "forge-config.yaml"
FORGE_DIR = ".forge"


def find_config(project_dir: str | Path | None = None) -> Path | None:
    """Auto-detect forge config in project workspace.

    Search order:
      1. .forge/forge.yaml (new canonical location)
      2. forge.yaml (project root)
      3. .forge/forge-config.yaml (legacy in .forge)
      4. forge-config.yaml (legacy project root)

    Args:
        project_dir: Directory to search. Defaults to cwd.

    Returns:
        Path to config file if found, None otherwise.
    """
    base = Path(project_dir) if project_dir else Path.cwd()
    candidates = [
        base / FORGE_DIR / CONFIG_FILENAME,
        base / CONFIG_FILENAME,
        base / FORGE_DIR / LEGACY_CONFIG_FILENAME,
        base / LEGACY_CONFIG_FILENAME,
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def load_config(path: str | Path) -> ForgeConfig:
    """Load a ForgeConfig from a YAML file."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path) as f:
        data = yaml.safe_load(f) or {}

    return ForgeConfig(**data)


def save_config(config: ForgeConfig, path: str | Path) -> None:
    """Save a ForgeConfig to a YAML file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    data = config.model_dump(mode="json")

    # Convert enums to their values for clean YAML
    def _clean(obj: object) -> object:
        if isinstance(obj, dict):
            return {k: _clean(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_clean(v) for v in obj]
        if hasattr(obj, "value"):
            return obj.value
        return obj

    data = _clean(data)

    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, width=120)


def ensure_forge_dir(project_dir: str | Path) -> Path:
    """Create .forge directory in project workspace and update .gitignore.

    Returns:
        Path to the .forge directory.
    """
    base = Path(project_dir)
    forge_dir = base / FORGE_DIR
    forge_dir.mkdir(parents=True, exist_ok=True)

    # Ensure .forge and .claude are in .gitignore
    gitignore = base / ".gitignore"
    entries_to_add = [".forge/", ".claude/"]
    existing_lines: list[str] = []
    if gitignore.exists():
        existing_lines = gitignore.read_text().splitlines()

    lines_added = False
    for entry in entries_to_add:
        if not any(line.strip() == entry for line in existing_lines):
            existing_lines.append(entry)
            lines_added = True

    if lines_added:
        gitignore.write_text("\n".join(existing_lines) + "\n")

    return forge_dir
