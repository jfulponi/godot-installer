"""Cross-platform desktop shortcut and system integration."""

from __future__ import annotations

import os
import platform
import stat
import subprocess
from pathlib import Path
from typing import Optional

from .paths import get_desktop_dir, get_applications_dir


def create_shortcut(
    executable: Path,
    name: str = "Godot Engine",
    icon_path: Optional[Path] = 'https://github.com/jfulponi/godot-installer/raw/refs/heads/master/assets/Godot_icon.ico',
    desktop: bool = True,
    menu: bool = True,
) -> list[Path]:
    """Create desktop and/or menu shortcuts. Returns list of created shortcut paths."""
    system = platform.system()
    created = []

    if system == "Windows":
        created.extend(_create_windows_shortcuts(executable, name, icon_path, desktop, menu))
    elif system == "Darwin":
        created.extend(_create_macos_shortcuts(executable, name, icon_path, desktop, menu))
    else:
        created.extend(_create_linux_shortcuts(executable, name, icon_path, desktop, menu))

    return created


def remove_shortcut(name: str = "Godot Engine") -> list[Path]:
    """Remove shortcuts for a given name. Returns list of removed paths."""
    system = platform.system()
    removed = []

    if system == "Windows":
        for d in [get_desktop_dir(), get_applications_dir()]:
            lnk = d / f"{name}.lnk"
            if lnk.exists():
                lnk.unlink()
                removed.append(lnk)

    elif system == "Darwin":
        alias = get_desktop_dir() / f"{name}.app"
        if alias.exists() or alias.is_symlink():
            alias.unlink()
            removed.append(alias)

    else:
        desktop_file = get_desktop_dir() / f"{_sanitize_name(name)}.desktop"
        menu_file = get_applications_dir() / f"{_sanitize_name(name)}.desktop"
        for f in [desktop_file, menu_file]:
            if f.exists():
                f.unlink()
                removed.append(f)

    return removed


# --- Windows ---

def _create_windows_shortcuts(
    executable: Path, name: str, icon_path: Optional[Path],
    desktop: bool, menu: bool,
) -> list[Path]:
    created = []
    targets = []
    if desktop:
        targets.append(get_desktop_dir() / f"{name}.lnk")
    if menu:
        menu_dir = get_applications_dir() / "Godot Engine"
        menu_dir.mkdir(parents=True, exist_ok=True)
        targets.append(menu_dir / f"{name}.lnk")

    for lnk_path in targets:
        try:
            _create_windows_lnk(executable, lnk_path, name, icon_path)
            created.append(lnk_path)
        except Exception:
            # Fallback: try PowerShell
            try:
                _create_windows_lnk_powershell(executable, lnk_path, name, icon_path)
                created.append(lnk_path)
            except Exception:
                pass

    return created


def _create_windows_lnk(
    target: Path, lnk_path: Path, description: str, icon_path: Optional[Path],
) -> None:
    """Create .lnk shortcut using COM (requires pywin32)."""
    import pythoncom
    from win32com.shell import shell
    import win32com.client

    ws = win32com.client.Dispatch("WScript.Shell")
    shortcut = ws.CreateShortCut(str(lnk_path))
    shortcut.Targetpath = str(target)
    shortcut.WorkingDirectory = str(target.parent)
    shortcut.Description = description
    if icon_path:
        shortcut.IconLocation = str(icon_path)
    else:
        shortcut.IconLocation = str(target)
    shortcut.save()


def _create_windows_lnk_powershell(
    target: Path, lnk_path: Path, description: str, icon_path: Optional[Path],
) -> None:
    """Fallback: create .lnk shortcut using PowerShell."""
    icon = str(icon_path) if icon_path else str(target)
    script = f"""
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut('{lnk_path}')
$s.TargetPath = '{target}'
$s.WorkingDirectory = '{target.parent}'
$s.Description = '{description}'
$s.IconLocation = '{icon}'
$s.Save()
"""
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True, timeout=15,
    )


# --- macOS ---

def _create_macos_shortcuts(
    executable: Path, name: str, icon_path: Optional[Path],
    desktop: bool, menu: bool,
) -> list[Path]:
    created = []

    # For .app bundles, symlink the whole .app
    app_bundle = _find_app_bundle(executable)
    source = app_bundle if app_bundle else executable

    if desktop:
        link = get_desktop_dir() / (f"{name}.app" if app_bundle else name)
        link.parent.mkdir(parents=True, exist_ok=True)
        if link.exists() or link.is_symlink():
            link.unlink()
        link.symlink_to(source)
        created.append(link)

    if menu and app_bundle:
        # Symlink into /Applications
        app_link = get_applications_dir() / app_bundle.name
        if app_link.exists() or app_link.is_symlink():
            app_link.unlink()
        try:
            app_link.symlink_to(source)
            created.append(app_link)
        except PermissionError:
            pass  # /Applications may need sudo

    return created


def _find_app_bundle(executable: Path) -> Optional[Path]:
    """Walk up from executable to find the .app bundle."""
    current = executable
    while current != current.parent:
        if current.suffix == ".app":
            return current
        current = current.parent
    # Also search in the version directory
    for p in executable.parent.rglob("*.app"):
        return p
    return None


# --- Linux ---

def _create_linux_shortcuts(
    executable: Path, name: str, icon_path: Optional[Path],
    desktop: bool, menu: bool,
) -> list[Path]:
    created = []
    sanitized = _sanitize_name(name)

    # Ensure executable permission
    if not os.access(executable, os.X_OK):
        executable.chmod(executable.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    desktop_entry = _generate_desktop_entry(executable, name, icon_path)

    if desktop:
        desktop_path = get_desktop_dir() / f"{sanitized}.desktop"
        desktop_path.parent.mkdir(parents=True, exist_ok=True)
        desktop_path.write_text(desktop_entry)
        desktop_path.chmod(desktop_path.stat().st_mode | stat.S_IEXEC)
        # Mark as trusted on GNOME
        try:
            subprocess.run(
                ["gio", "set", str(desktop_path), "metadata::trusted", "true"],
                capture_output=True, timeout=5,
            )
        except Exception:
            pass
        created.append(desktop_path)

    if menu:
        menu_path = get_applications_dir() / f"{sanitized}.desktop"
        menu_path.parent.mkdir(parents=True, exist_ok=True)
        menu_path.write_text(desktop_entry)
        created.append(menu_path)
        # Update desktop database
        try:
            subprocess.run(
                ["update-desktop-database", str(get_applications_dir())],
                capture_output=True, timeout=10,
            )
        except Exception:
            pass

    return created


def _generate_desktop_entry(
    executable: Path, name: str, icon_path: Optional[Path],
) -> str:
    icon_line = f"Icon={icon_path}" if icon_path else f"Icon={executable}"
    return f"""[Desktop Entry]
Type=Application
Name={name}
Comment=Godot Engine - Game Development Environment
Exec={executable}
{icon_line}
Terminal=false
Categories=Development;IDE;
Keywords=godot;game;engine;gamedev;
StartupWMClass=Godot
"""


def _sanitize_name(name: str) -> str:
    return name.lower().replace(" ", "-").replace(".", "-")
