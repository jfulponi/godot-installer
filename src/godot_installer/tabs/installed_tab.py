"""Installed tab — manage installed Godot versions."""

from __future__ import annotations

import subprocess
import platform
import threading
from pathlib import Path
from typing import TYPE_CHECKING

import customtkinter as ctk

from ..versions import get_installed_versions, find_godot_executable, remove_version
from ..shortcuts import create_shortcut, remove_shortcut
from ..paths import get_versions_dir
from ..config import load_config, save_config

if TYPE_CHECKING:
    from ..app import GodotInstallerApp


class InstalledTab:
    def __init__(self, parent: ctk.CTkFrame, app: GodotInstallerApp):
        self.parent = parent
        self.app = app
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        # Top controls
        controls = ctk.CTkFrame(self.parent, fg_color="transparent")
        controls.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(
            controls,
            text="Installed Versions",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(side="left")

        open_folder_btn = ctk.CTkButton(
            controls,
            text="Open Folder",
            width=110,
            command=self._open_versions_folder,
        )
        open_folder_btn.pack(side="right", padx=5)

        refresh_btn = ctk.CTkButton(
            controls,
            text="↻ Refresh",
            width=90,
            command=self.refresh,
        )
        refresh_btn.pack(side="right", padx=5)

        # Versions list
        self.list_frame = ctk.CTkScrollableFrame(self.parent, corner_radius=8)
        self.list_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))

    def refresh(self):
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        installed = get_installed_versions()

        if not installed:
            empty = ctk.CTkFrame(self.list_frame, fg_color="transparent")
            empty.pack(fill="both", expand=True, pady=60)
            ctk.CTkLabel(
                empty,
                text="No Godot versions installed yet",
                font=ctk.CTkFont(size=16),
                text_color="gray50",
            ).pack()
            ctk.CTkLabel(
                empty,
                text="Go to the Install tab to download a version",
                font=ctk.CTkFont(size=13),
                text_color="gray40",
            ).pack(pady=(5, 0))
            return

        default_version = self.app.config_data.get("default_version", "")

        for v in installed:
            self._add_version_card(v, is_default=(v["version"] == default_version))

    def _add_version_card(self, version_info: dict, is_default: bool):
        card = ctk.CTkFrame(self.list_frame, corner_radius=8, fg_color=("gray88", "gray22"))
        card.pack(fill="x", pady=4)

        # Left: version info
        info_frame = ctk.CTkFrame(card, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True, padx=15, pady=12)

        # Version name + default badge
        name_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        name_frame.pack(anchor="w")

        version_name = version_info["version"]
        display_name = version_name.replace("-standard", "").replace("-mono", " (Mono)")

        ctk.CTkLabel(
            name_frame,
            text=display_name,
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(side="left")

        if is_default:
            ctk.CTkLabel(
                name_frame,
                text="  DEFAULT",
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color="#4CAF50",
            ).pack(side="left", padx=(8, 0))

        # Path
        ctk.CTkLabel(
            info_frame,
            text=version_info["path"],
            font=ctk.CTkFont(size=11),
            text_color="gray50",
            anchor="w",
        ).pack(anchor="w", pady=(2, 0))

        # Executable status
        exe = version_info.get("executable")
        if exe:
            ctk.CTkLabel(
                info_frame,
                text=f"Executable: {Path(exe).name}",
                font=ctk.CTkFont(size=11),
                text_color="gray45",
                anchor="w",
            ).pack(anchor="w")
        else:
            ctk.CTkLabel(
                info_frame,
                text="Executable not found",
                font=ctk.CTkFont(size=11),
                text_color="#F44336",
                anchor="w",
            ).pack(anchor="w")

        # Right: action buttons
        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.pack(side="right", padx=15, pady=12)

        # Launch button
        launch_btn = ctk.CTkButton(
            btn_frame,
            text="▶  Launch",
            width=100,
            height=32,
            fg_color="#4CAF50",
            hover_color="#388E3C",
            state="normal" if exe else "disabled",
            command=lambda: self._launch(exe),
        )
        launch_btn.pack(pady=(0, 4))

        # Set as default
        if not is_default:
            default_btn = ctk.CTkButton(
                btn_frame,
                text="Set Default",
                width=100,
                height=28,
                fg_color=("gray70", "gray35"),
                hover_color=("gray60", "gray40"),
                command=lambda vn=version_name: self._set_default(vn),
            )
            default_btn.pack(pady=2)

        # Shortcut button
        shortcut_btn = ctk.CTkButton(
            btn_frame,
            text="+ Shortcut",
            width=100,
            height=28,
            fg_color=("gray70", "gray35"),
            hover_color=("gray60", "gray40"),
            state="normal" if exe else "disabled",
            command=lambda: self._create_shortcut(version_info),
        )
        shortcut_btn.pack(pady=2)

        # Remove button
        remove_btn = ctk.CTkButton(
            btn_frame,
            text="Remove",
            width=100,
            height=28,
            fg_color="#C62828",
            hover_color="#B71C1C",
            command=lambda vn=version_name: self._remove(vn),
        )
        remove_btn.pack(pady=(2, 0))

    def _launch(self, exe_path: str | None):
        if not exe_path:
            return
        try:
            exe = Path(exe_path)
            # Make executable on Unix
            if platform.system() != "Windows":
                import os, stat
                if not os.access(exe, os.X_OK):
                    exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
            subprocess.Popen([str(exe)])
            self.app.set_status(f"Launched {exe.name}")
        except Exception as e:
            self.app.set_status(f"Launch failed: {e}")

    def _set_default(self, version_name: str):
        self.app.config_data["default_version"] = version_name
        self.app.save_config()
        self.app.set_status(f"Default set to {version_name}")
        self.refresh()

    def _create_shortcut(self, version_info: dict):
        exe = version_info.get("executable")
        if not exe:
            return
        name = version_info["version"].replace("-standard", "").replace("-mono", " (Mono)")
        shortcut_name = f"Godot {name}"
        created = create_shortcut(Path(exe), name=shortcut_name)
        if created:
            self.app.set_status(f"Shortcut created: {created[0]}")
        else:
            self.app.set_status("Failed to create shortcut")

    def _remove(self, version_name: str):
        # Confirm dialog
        dialog = ctk.CTkToplevel(self.parent)
        dialog.title("Confirm Removal")
        dialog.geometry("400x160")
        dialog.resizable(False, False)
        dialog.grab_set()
        dialog.transient(self.parent)

        ctk.CTkLabel(
            dialog,
            text=f"Remove Godot {version_name}?",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(pady=(20, 5))

        ctk.CTkLabel(
            dialog,
            text="This will delete the version files and shortcuts.",
            font=ctk.CTkFont(size=12),
            text_color="gray50",
        ).pack()

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=15)

        def do_remove():
            dialog.destroy()
            display = version_name.replace("-standard", "").replace("-mono", " (Mono)")
            remove_shortcut(f"Godot {display}")
            if remove_version(version_name):
                # Update default
                if self.app.config_data.get("default_version") == version_name:
                    installed = get_installed_versions()
                    self.app.config_data["default_version"] = installed[0]["version"] if installed else None
                    self.app.save_config()
                self.app.set_status(f"Removed {version_name}")
                self.refresh()
            else:
                self.app.set_status(f"Failed to remove {version_name}")

        ctk.CTkButton(
            btn_frame, text="Remove", fg_color="#C62828", hover_color="#B71C1C",
            width=100, command=do_remove,
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            btn_frame, text="Cancel", fg_color=("gray70", "gray35"),
            width=100, command=dialog.destroy,
        ).pack(side="left", padx=10)

    def _open_versions_folder(self):
        folder = get_versions_dir()
        folder.mkdir(parents=True, exist_ok=True)
        system = platform.system()
        try:
            if system == "Windows":
                subprocess.Popen(["explorer", str(folder)])
            elif system == "Darwin":
                subprocess.Popen(["open", str(folder)])
            else:
                subprocess.Popen(["xdg-open", str(folder)])
        except Exception as e:
            self.app.set_status(f"Could not open folder: {e}")
