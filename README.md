# Godot Installer

Cross-platform Godot Engine version manager and installer. Download, install, and manage multiple Godot versions with native desktop integration (shortcuts, start menu entries).

## Features

- **Download & install** any Godot version (stable or pre-release) from GitHub
- **Desktop shortcuts** — Windows (.lnk + Start Menu), Linux (.desktop), macOS (symlink + /Applications)
- **Version management** — install multiple versions, switch between them, set a default
- **Mono/.NET support** — install standard or Mono builds
- **Cross-platform** — Windows, Linux, macOS
- **Auto-release detection** — GitHub Actions workflow checks for new Godot releases every 6 hours and builds new installers automatically

## Installation

### Download a pre-built binary

Go to [Releases](../../releases) and download the binary for your platform:

| Platform | File |
|----------|------|
| Windows  | `godot-installer-windows.exe` |
| Linux    | `godot-installer-linux` |
| macOS    | `godot-installer-macos` |

### Install from source

```bash
pip install -e .
```

## Usage

```bash
# Install the latest stable Godot
godot-installer install latest

# List available versions
godot-installer list
godot-installer list --all          # include pre-releases

# Install a specific version
godot-installer install 4.4
godot-installer install 4.3 --mono  # Mono/.NET build

# List installed versions
godot-installer list --installed

# Launch Godot
godot-installer run              # runs default version
godot-installer run 4.4          # runs specific version

# Set default version
godot-installer use 4.4

# Manage shortcuts
godot-installer shortcut create 4.4
godot-installer shortcut remove 4.4

# Remove a version
godot-installer remove 4.3

# Configuration
godot-installer config                          # show all
godot-installer config github_token ghp_xxx     # set GitHub token (for higher API limits)
godot-installer config mono true                # default to Mono builds
```

## Desktop Integration

When you install a Godot version, the installer automatically:

- **Windows**: Creates a `.lnk` shortcut on the Desktop and in Start Menu → Programs → Godot Engine
- **Linux**: Creates a `.desktop` file on the Desktop and in `~/.local/share/applications/` (shows in app launcher)
- **macOS**: Creates a symlink on the Desktop and in `/Applications`

Use `--no-shortcut` to skip shortcut creation.

## GitHub Token

To avoid GitHub API rate limits (60 req/hour unauthenticated), set a personal access token:

```bash
godot-installer config github_token ghp_your_token_here
# or
export GITHUB_TOKEN=ghp_your_token_here
```

No special scopes are needed — a fine-grained token with public repo read access is sufficient.

## Building from Source

### Build a standalone executable

```bash
pip install pyinstaller
pip install -e ".[dev]"

pyinstaller --onefile --name godot-installer \
  --add-data "src/godot_installer:godot_installer" \
  --hidden-import=godot_installer \
  --hidden-import=godot_installer.cli \
  --hidden-import=godot_installer.versions \
  --hidden-import=godot_installer.shortcuts \
  --hidden-import=godot_installer.paths \
  --hidden-import=godot_installer.config \
  src/godot_installer/cli.py
```

The executable will be in `dist/`.

### CI/CD

The project includes GitHub Actions workflows:

- **`build.yml`** — Builds executables for Windows, Linux, macOS on tag push. Creates a GitHub release with all binaries.
- **`check-godot-releases.yml`** — Runs every 6 hours, detects new Godot releases, and triggers automatic builds.
- **`build-for-godot-release.yml`** — Builds version-specific installers when a new Godot release is detected.

#### Creating a release

```bash
git tag v1.0.0
git push origin v1.0.0
# GitHub Actions will build and create the release automatically
```

#### Manual trigger

You can also trigger builds manually from the Actions tab in GitHub.

## Data Locations

| | Windows | Linux | macOS |
|---|---|---|---|
| Versions | `%LOCALAPPDATA%/GodotInstaller/versions` | `~/.local/share/GodotInstaller/versions` | `~/Library/Application Support/GodotInstaller/versions` |
| Cache | `%LOCALAPPDATA%/GodotInstaller/Cache` | `~/.cache/GodotInstaller` | `~/Library/Caches/GodotInstaller` |
| Config | `%LOCALAPPDATA%/GodotInstaller/config.json` | `~/.config/GodotInstaller/config.json` | `~/Library/Application Support/GodotInstaller/config.json` |

## License

MIT
