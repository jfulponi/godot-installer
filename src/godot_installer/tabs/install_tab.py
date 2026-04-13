"""Install tab — browse and download Godot versions."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

import customtkinter as ctk

from ..config import get_github_token
from ..versions import fetch_releases, download_godot, find_godot_executable, GodotRelease
from ..shortcuts import create_shortcut

if TYPE_CHECKING:
    from ..app import GodotInstallerApp


class InstallTab:
    def __init__(self, parent: ctk.CTkFrame, app: GodotInstallerApp):
        self.parent = parent
        self.app = app
        self.releases: list[GodotRelease] = []
        self.filtered_releases: list[GodotRelease] = []
        self._downloading = False

        self._build_ui()
        # Auto-fetch on start
        threading.Thread(target=self._fetch_versions, daemon=True).start()

    def _build_ui(self):
        # Top controls
        controls = ctk.CTkFrame(self.parent, fg_color="transparent")
        controls.pack(fill="x", padx=10, pady=(10, 5))

        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._filter_list())

        search_entry = ctk.CTkEntry(
            controls,
            placeholder_text="Search versions (e.g. 4.4, 3.5)...",
            textvariable=self.search_var,
            width=250,
        )
        search_entry.pack(side="left", padx=(0, 10))

        self.show_prerelease = ctk.BooleanVar(value=False)
        pre_check = ctk.CTkCheckBox(
            controls,
            text="Include pre-releases",
            variable=self.show_prerelease,
            command=self._on_prerelease_toggle,
        )
        pre_check.pack(side="left", padx=(0, 10))

        self.mono_var = ctk.BooleanVar(value=False)
        mono_check = ctk.CTkCheckBox(
            controls,
            text="Mono / .NET",
            variable=self.mono_var,
        )
        mono_check.pack(side="left", padx=(0, 10))

        refresh_btn = ctk.CTkButton(
            controls,
            text="↻ Refresh",
            width=100,
            command=lambda: threading.Thread(target=self._fetch_versions, daemon=True).start(),
        )
        refresh_btn.pack(side="right")

        # Versions list
        self.list_frame = ctk.CTkScrollableFrame(self.parent, corner_radius=8)
        self.list_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Loading label (shown initially)
        self.loading_label = ctk.CTkLabel(
            self.list_frame,
            text="Loading versions from GitHub...",
            font=ctk.CTkFont(size=14),
            text_color="gray50",
        )
        self.loading_label.pack(pady=40)

        # Bottom: download progress
        bottom = ctk.CTkFrame(self.parent, fg_color="transparent")
        bottom.pack(fill="x", padx=10, pady=(5, 10))

        self.progress_bar = ctk.CTkProgressBar(bottom, height=18)
        self.progress_bar.pack(fill="x", pady=(0, 4))
        self.progress_bar.set(0)

        self.progress_label = ctk.CTkLabel(
            bottom,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray50",
        )
        self.progress_label.pack(anchor="w")

    def _fetch_versions(self):
        self.parent.after(0, lambda: self.app.set_status("Fetching versions from GitHub..."))
        try:
            token = get_github_token(self.app.config_data)
            self.releases = fetch_releases(
                include_prerelease=self.show_prerelease.get(),
                github_token=token,
                limit=50,
            )
            self.parent.after(0, self._populate_list)
            self.parent.after(0, lambda: self.app.set_status(f"Found {len(self.releases)} versions"))
        except Exception as e:
            self.parent.after(0, lambda: self.app.set_status(f"Error: {e}"))

    def _on_prerelease_toggle(self):
        threading.Thread(target=self._fetch_versions, daemon=True).start()

    def _filter_list(self):
        query = self.search_var.get().strip().lower()
        if not query:
            self.filtered_releases = list(self.releases)
        else:
            self.filtered_releases = [
                r for r in self.releases
                if query in r.version.lower() or query in r.tag.lower()
            ]
        self._render_list()

    def _populate_list(self):
        self.filtered_releases = list(self.releases)
        self._render_list()

    def _render_list(self):
        # Clear current items
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        if not self.filtered_releases:
            ctk.CTkLabel(
                self.list_frame,
                text="No versions found.",
                font=ctk.CTkFont(size=14),
                text_color="gray50",
            ).pack(pady=40)
            return

        # Header
        header = ctk.CTkFrame(self.list_frame, fg_color=("gray78", "gray25"), corner_radius=6)
        header.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(header, text="Version", font=ctk.CTkFont(weight="bold"), width=120, anchor="w").pack(side="left", padx=10, pady=6)
        ctk.CTkLabel(header, text="Type", font=ctk.CTkFont(weight="bold"), width=100, anchor="w").pack(side="left", padx=5)
        ctk.CTkLabel(header, text="Asset", font=ctk.CTkFont(weight="bold"), width=300, anchor="w").pack(side="left", padx=5)
        ctk.CTkLabel(header, text="", width=120).pack(side="right", padx=10)

        for release in self.filtered_releases:
            self._add_version_row(release)

    def _add_version_row(self, release: GodotRelease):
        row = ctk.CTkFrame(self.list_frame, fg_color=("gray90", "gray20"), corner_radius=6, height=42)
        row.pack(fill="x", pady=2)
        row.pack_propagate(False)

        # Version
        color = "#4CAF50" if release.is_stable else "#FFC107"
        ctk.CTkLabel(
            row,
            text=release.version,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=color,
            width=120,
            anchor="w",
        ).pack(side="left", padx=10, pady=6)

        # Type badge
        type_text = "stable" if release.is_stable else "pre-release"
        ctk.CTkLabel(
            row,
            text=type_text,
            font=ctk.CTkFont(size=11),
            text_color="gray50",
            width=100,
            anchor="w",
        ).pack(side="left", padx=5)

        # Asset name
        asset = release.find_asset(self.mono_var.get())
        asset_text = asset["name"] if asset else "No compatible build"
        asset_color = "gray60" if asset else "#F44336"
        ctk.CTkLabel(
            row,
            text=asset_text,
            font=ctk.CTkFont(size=11),
            text_color=asset_color,
            width=300,
            anchor="w",
        ).pack(side="left", padx=5)

        # Install button
        btn = ctk.CTkButton(
            row,
            text="Install",
            width=90,
            height=28,
            font=ctk.CTkFont(size=12),
            state="normal" if asset else "disabled",
            command=lambda r=release: self._start_install(r),
        )
        btn.pack(side="right", padx=10, pady=6)

    def _start_install(self, release: GodotRelease):
        if self._downloading:
            return
        self._downloading = True
        self.progress_bar.set(0)
        self.progress_label.configure(text=f"Downloading Godot {release.version}...")
        self.app.set_status(f"Installing Godot {release.version}...")

        threading.Thread(
            target=self._do_install,
            args=(release,),
            daemon=True,
        ).start()

    def _do_install(self, release: GodotRelease):
        try:
            mono = self.mono_var.get()
            token = get_github_token(self.app.config_data)

            def on_progress(downloaded, total):
                frac = downloaded / total if total else 0
                mb_down = downloaded / (1024 * 1024)
                mb_total = total / (1024 * 1024)
                self.parent.after(0, lambda: self.progress_bar.set(frac))
                self.parent.after(
                    0,
                    lambda: self.progress_label.configure(
                        text=f"Downloading... {mb_down:.1f} / {mb_total:.1f} MB ({frac * 100:.0f}%)"
                    ),
                )

            version_dir = download_godot(
                release, mono=mono, progress_callback=on_progress, github_token=token,
            )

            exe = find_godot_executable(version_dir)

            # Create shortcut
            shortcut_name = f"Godot {release.version}"
            if mono:
                shortcut_name += " (Mono)"
            shortcuts_created = []
            if exe and self.app.config_data.get("auto_shortcut", True):
                shortcuts_created = create_shortcut(exe, name=shortcut_name)

            # Set as default if none set
            if not self.app.config_data.get("default_version"):
                self.app.config_data["default_version"] = version_dir.name
                self.app.save_config()

            def _on_done():
                self.progress_bar.set(1)
                msg = f"Godot {release.version} installed!"
                if shortcuts_created:
                    msg += f" Shortcut created."
                self.progress_label.configure(text=msg)
                self.app.set_status(msg)
                self.app.refresh_installed()
                self._downloading = False

            self.parent.after(0, _on_done)

        except Exception as e:
            def _on_error():
                self.progress_bar.set(0)
                self.progress_label.configure(text=f"Error: {e}")
                self.app.set_status(f"Install failed: {e}")
                self._downloading = False

            self.parent.after(0, _on_error)
