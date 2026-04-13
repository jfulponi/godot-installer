"""Cross-platform path management for Godot Installer."""

from __future__ import annotations

import platform
from pathlib import Path

import platformdirs


APP_NAME = "GodotInstaller"
APP_AUTHOR = "GodotInstaller"


def get_data_dir() -> Path:
    """Get the platform-appropriate data directory."""
    return Path(platformdirs.user_data_dir(APP_NAME, APP_AUTHOR))


def get_versions_dir() -> Path:
    """Directory where Godot versions are stored."""
    return get_data_dir() / "versions"


def get_cache_dir() -> Path:
    """Directory for downloaded archives."""
    return Path(platformdirs.user_cache_dir(APP_NAME, APP_AUTHOR))


def get_config_dir() -> Path:
    """Directory for configuration files."""
    return Path(platformdirs.user_config_dir(APP_NAME, APP_AUTHOR))


def get_config_file() -> Path:
    """Path to the main config file."""
    return get_config_dir() / "config.json"


def get_desktop_dir() -> Path:
    """Get the user's Desktop directory."""
    system = platform.system()

    if system == "Windows":
        # Use Windows known folder
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders",
            )
            desktop, _ = winreg.QueryValueEx(key, "Desktop")
            winreg.CloseKey(key)
            return Path(desktop)
        except Exception:
            pass
        return Path.home() / "Desktop"

    elif system == "Darwin":
        return Path.home() / "Desktop"

    else:  # Linux and others
        # Try XDG
        try:
            import subprocess
            result = subprocess.run(
                ["xdg-user-dir", "DESKTOP"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                return Path(result.stdout.strip())
        except Exception:
            pass
        return Path.home() / "Desktop"


def get_applications_dir() -> Path:
    """Get the platform-specific applications directory for integration."""
    system = platform.system()

    if system == "Windows":
        # Start Menu programs
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders",
            )
            programs, _ = winreg.QueryValueEx(key, "Programs")
            winreg.CloseKey(key)
            return Path(programs)
        except Exception:
            pass
        return Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs"

    elif system == "Darwin":
        return Path("/Applications")

    else:  # Linux
        return Path.home() / ".local" / "share" / "applications"
