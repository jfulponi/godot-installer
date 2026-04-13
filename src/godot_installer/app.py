"""Main GUI application for Godot Installer."""

from __future__ import annotations

import threading
import customtkinter as ctk

from . import __version__
from .config import load_config, save_config
from .tabs.install_tab import InstallTab
from .tabs.installed_tab import InstalledTab
from .tabs.settings_tab import SettingsTab


class GodotInstallerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(f"Godot Installer v{__version__}")
        self.geometry("900x620")
        self.minsize(750, 500)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.config_data = load_config()

        self._build_ui()

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, height=60, corner_radius=0, fg_color=("gray85", "gray17"))
        header.pack(fill="x")
        header.pack_propagate(False)

        title_label = ctk.CTkLabel(
            header,
            text="⬡  Godot Installer",
            font=ctk.CTkFont(size=22, weight="bold"),
        )
        title_label.pack(side="left", padx=20, pady=10)

        version_label = ctk.CTkLabel(
            header,
            text=f"v{__version__}",
            font=ctk.CTkFont(size=12),
            text_color="gray50",
        )
        version_label.pack(side="left", pady=10)

        # Tabview
        self.tabview = ctk.CTkTabview(self, corner_radius=8)
        self.tabview.pack(fill="both", expand=True, padx=15, pady=(10, 15))

        tab_install = self.tabview.add("  Install  ")
        tab_installed = self.tabview.add("  Installed  ")
        tab_settings = self.tabview.add("  Settings  ")

        self.install_tab = InstallTab(tab_install, self)
        self.installed_tab = InstalledTab(tab_installed, self)
        self.settings_tab = SettingsTab(tab_settings, self)

        # Status bar
        self.status_bar = ctk.CTkFrame(self, height=28, corner_radius=0, fg_color=("gray85", "gray17"))
        self.status_bar.pack(fill="x", side="bottom")
        self.status_bar.pack_propagate(False)

        self.status_label = ctk.CTkLabel(
            self.status_bar,
            text="Ready",
            font=ctk.CTkFont(size=11),
            text_color="gray50",
        )
        self.status_label.pack(side="left", padx=15)

    def set_status(self, text: str):
        self.status_label.configure(text=text)

    def save_config(self):
        save_config(self.config_data)

    def refresh_installed(self):
        """Refresh the installed tab after an install/remove."""
        self.installed_tab.refresh()


def main():
    app = GodotInstallerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
