"""Settings tab — configuration and preferences."""

from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk

from ..paths import get_data_dir, get_cache_dir, get_config_dir

if TYPE_CHECKING:
    from ..app import GodotInstallerApp


class SettingsTab:
    def __init__(self, parent: ctk.CTkFrame, app: GodotInstallerApp):
        self.parent = parent
        self.app = app
        self._build_ui()

    def _build_ui(self):
        container = ctk.CTkScrollableFrame(self.parent, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=10, pady=10)

        # --- GitHub Token ---
        self._section(container, "GitHub Token", "Avoids API rate limits (60 req/hour without token)")

        token_frame = ctk.CTkFrame(container, fg_color="transparent")
        token_frame.pack(fill="x", padx=20, pady=(0, 15))

        self.token_var = ctk.StringVar(value=self.app.config_data.get("github_token") or "")
        token_entry = ctk.CTkEntry(
            token_frame,
            textvariable=self.token_var,
            placeholder_text="ghp_xxxxxxxxxxxxxxxxxxxx",
            width=400,
            show="*",
        )
        token_entry.pack(side="left", padx=(0, 10))

        self.show_token_var = ctk.BooleanVar(value=False)
        show_btn = ctk.CTkCheckBox(
            token_frame,
            text="Show",
            variable=self.show_token_var,
            command=lambda: token_entry.configure(show="" if self.show_token_var.get() else "*"),
            width=60,
        )
        show_btn.pack(side="left", padx=(0, 10))

        save_token_btn = ctk.CTkButton(
            token_frame,
            text="Save Token",
            width=100,
            command=self._save_token,
        )
        save_token_btn.pack(side="left")

        ctk.CTkLabel(
            container,
            text="A fine-grained GitHub token with public repo read access is sufficient.",
            font=ctk.CTkFont(size=11),
            text_color="gray45",
        ).pack(anchor="w", padx=20, pady=(0, 15))

        # --- Preferences ---
        self._section(container, "Preferences", "Default behavior when installing versions")

        prefs_frame = ctk.CTkFrame(container, fg_color="transparent")
        prefs_frame.pack(fill="x", padx=20, pady=(0, 15))

        self.auto_shortcut_var = ctk.BooleanVar(
            value=self.app.config_data.get("auto_shortcut", True)
        )
        ctk.CTkCheckBox(
            prefs_frame,
            text="Automatically create desktop shortcut on install",
            variable=self.auto_shortcut_var,
            command=self._save_prefs,
        ).pack(anchor="w", pady=3)

        self.mono_default_var = ctk.BooleanVar(
            value=self.app.config_data.get("mono", False)
        )
        ctk.CTkCheckBox(
            prefs_frame,
            text="Default to Mono / .NET builds",
            variable=self.mono_default_var,
            command=self._save_prefs,
        ).pack(anchor="w", pady=3)

        self.prerelease_default_var = ctk.BooleanVar(
            value=self.app.config_data.get("include_prerelease", False)
        )
        ctk.CTkCheckBox(
            prefs_frame,
            text="Show pre-release versions by default",
            variable=self.prerelease_default_var,
            command=self._save_prefs,
        ).pack(anchor="w", pady=3)

        # --- Appearance ---
        self._section(container, "Appearance", "Visual theme")

        appearance_frame = ctk.CTkFrame(container, fg_color="transparent")
        appearance_frame.pack(fill="x", padx=20, pady=(0, 15))

        ctk.CTkLabel(appearance_frame, text="Theme:").pack(side="left", padx=(0, 10))
        theme_menu = ctk.CTkOptionMenu(
            appearance_frame,
            values=["Dark", "Light", "System"],
            command=self._change_theme,
            width=120,
        )
        theme_menu.set(self.app.config_data.get("theme", "Dark"))
        theme_menu.pack(side="left")

        # --- Paths info ---
        self._section(container, "Storage Paths", "Where data is stored on this system")

        paths_frame = ctk.CTkFrame(container, fg_color=("gray88", "gray22"), corner_radius=8)
        paths_frame.pack(fill="x", padx=20, pady=(0, 15))

        paths = [
            ("Versions", str(get_data_dir() / "versions")),
            ("Cache", str(get_cache_dir())),
            ("Config", str(get_config_dir())),
        ]
        for label, path in paths:
            row = ctk.CTkFrame(paths_frame, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=4)
            ctk.CTkLabel(row, text=f"{label}:", font=ctk.CTkFont(weight="bold"), width=80, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=path, font=ctk.CTkFont(size=11), text_color="gray50").pack(side="left", padx=5)

        # --- Clear cache ---
        cache_frame = ctk.CTkFrame(container, fg_color="transparent")
        cache_frame.pack(fill="x", padx=20, pady=(5, 15))

        ctk.CTkButton(
            cache_frame,
            text="Clear Download Cache",
            width=180,
            fg_color=("gray70", "gray35"),
            hover_color=("gray60", "gray40"),
            command=self._clear_cache,
        ).pack(side="left")

    def _section(self, parent, title: str, subtitle: str):
        ctk.CTkLabel(
            parent,
            text=title,
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(15, 0))
        ctk.CTkLabel(
            parent,
            text=subtitle,
            font=ctk.CTkFont(size=11),
            text_color="gray45",
        ).pack(anchor="w", padx=10, pady=(0, 8))

    def _save_token(self):
        token = self.token_var.get().strip()
        self.app.config_data["github_token"] = token if token else None
        self.app.save_config()
        self.app.set_status("GitHub token saved" if token else "GitHub token removed")

    def _save_prefs(self):
        self.app.config_data["auto_shortcut"] = self.auto_shortcut_var.get()
        self.app.config_data["mono"] = self.mono_default_var.get()
        self.app.config_data["include_prerelease"] = self.prerelease_default_var.get()
        self.app.save_config()
        self.app.set_status("Preferences saved")

    def _change_theme(self, value: str):
        ctk.set_appearance_mode(value.lower())
        self.app.config_data["theme"] = value
        self.app.save_config()

    def _clear_cache(self):
        import shutil
        cache = get_cache_dir()
        if cache.exists():
            shutil.rmtree(cache)
            cache.mkdir(parents=True, exist_ok=True)
            self.app.set_status("Cache cleared")
        else:
            self.app.set_status("Cache is already empty")
