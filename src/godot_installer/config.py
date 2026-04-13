"""Configuration management."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .paths import get_config_file


DEFAULT_CONFIG = {
    "default_version": None,
    "mono": False,
    "include_prerelease": False,
    "github_token": None,
    "auto_shortcut": True,
}


def load_config() -> dict:
    config_file = get_config_file()
    config = dict(DEFAULT_CONFIG)
    if config_file.exists():
        try:
            with open(config_file) as f:
                stored = json.load(f)
            config.update(stored)
        except (json.JSONDecodeError, IOError):
            pass
    return config


def save_config(config: dict) -> None:
    config_file = get_config_file()
    config_file.parent.mkdir(parents=True, exist_ok=True)
    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)


def get_github_token(config: dict) -> Optional[str]:
    """Get GitHub token from config or environment."""
    import os
    return config.get("github_token") or os.environ.get("GITHUB_TOKEN")
