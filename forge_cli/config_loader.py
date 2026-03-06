"""Load and validate forge configuration from YAML."""

from __future__ import annotations

from pathlib import Path

import yaml

from forge_cli.config_schema import ForgeConfig


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
    def _clean(obj):
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
