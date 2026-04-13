# Godot Installer

A graphical Godot Engine version manager. Download, install, and manage multiple Godot versions with one click — complete with desktop shortcuts, Start Menu entries, and app launcher integration.

![Python](https://img.shields.io/badge/python-3.9+-blue)
![Platforms](https://img.shields.io/badge/platforms-Windows%20%7C%20Linux%20%7C%20macOS-green)
![License](https://img.shields.io/badge/license-MIT-orange)

## Features

- **One-click install** — Browse all available Godot versions and install with a single button
- **Desktop shortcuts** — Automatically creates:
  - Windows: Desktop `.lnk` + Start Menu entry
  - Linux: `.desktop` file + app launcher integration
  - macOS: Desktop symlink + `/Applications` link
- **Version management** — Install multiple versions side by side, set a default, launch any version
- **Mono / .NET support** — Toggle to download Mono builds
- **Download progress** — Real-time progress bar with speed and size info
- **Dark/Light theme** — Switch between dark, light, or system theme
- **Auto-release detection** — CI/CD watches for new Godot releases and builds fresh installers

## Download

Go to [Releases](../../releases) and grab the binary for your OS:

| Platform | File |
|----------|------|
| Windows  | `godot-installer-windows.exe` |
| Linux    | `godot-installer-linux` |
| macOS    | `godot-installer-macos` |

Double-click to run — no installation needed.

## Usage

### Install tab
Browse all available Godot versions. Search by version number, toggle pre-releases or Mono builds, and click **Install** on any version. A progress bar shows the download status, and a desktop shortcut is created automatically.

### Installed tab
See all your installed versions at a glance. From here you can:
- **Launch** any version with one click
- **Set Default** version
- **Create/remove shortcuts**
- **Remove** versions you no longer need
- **Open** the versions folder in your file manager

### Settings tab
- **GitHub Token** — Set a personal access token to avoid API rate limits
- **Preferences** — Auto-shortcut, default to Mono, show pre-releases
- **Theme** — Dark, Light, or System
- **Clear cache** — Remove downloaded ZIP files

## Run from Source

```bash
git clone https://github.com/YOUR_USER/godot-installer.git
cd godot-installer
pip install -e .
python -m godot_installer.app
```

## Build a Standalone Executable

```bash
pip install pyinstaller
pip install -e ".[dev]"

pyinstaller --onefile --windowed --name godot-installer \
  --add-data "src/godot_installer:godot_installer" \
  --hidden-import=godot_installer \
  --hidden-import=godot_installer.app \
  --hidden-import=godot_installer.tabs.install_tab \
  --hidden-import=godot_installer.tabs.installed_tab \
  --hidden-import=godot_installer.tabs.settings_tab \
  --hidden-import=customtkinter \
  --collect-all customtkinter \
  src/godot_installer/app.py
```

Output: `dist/godot-installer` (or `.exe` on Windows).

## CI/CD

Three GitHub Actions workflows are included:

| Workflow | Trigger | What it does |
|----------|---------|--------------|
| `build.yml` | Tag push (`v*`) or manual | Builds for Win/Linux/Mac, creates GitHub release |
| `check-godot-releases.yml` | Every 6 hours (cron) | Detects new Godot stable/pre-release versions |
| `build-for-godot-release.yml` | Auto (from check) or manual | Builds version-specific installers as release assets |

### Quick release

```bash
git tag v1.0.0
git push origin v1.0.0
```

GitHub Actions will build all 3 platform binaries and attach them to a new release.

### Auto-detection

The `check-godot-releases.yml` cron job checks the Godot GitHub repo every 6 hours. When a new stable version is detected, it:
1. Opens an issue notifying about the new release
2. Triggers `build-for-godot-release.yml` which builds new installers
3. Creates a tagged release with the platform binaries as assets

## License

MIT
