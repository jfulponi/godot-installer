"""Godot version discovery and download management via GitHub API."""

from __future__ import annotations

import hashlib
import platform
import re
import shutil
import zipfile
from pathlib import Path
from typing import Optional

import requests

from .paths import get_versions_dir, get_cache_dir

GODOT_REPO = "godotengine/godot"
GODOT_BUILDS_REPO = "godotengine/godot-builds"
GITHUB_API = "https://api.github.com"

# Map (os, arch, mono) -> filename patterns in Godot releases
_PLATFORM_PATTERNS: dict[tuple[str, bool], list[str]] = {
    ("Windows", False): ["win64.exe.zip", "win32.exe.zip"],
    ("Windows", True): ["mono_win64.zip", "mono_win32.zip"],
    ("Linux", False): ["linux.x86_64.zip", "linux_x86_64.zip", "linux.64.zip"],
    ("Linux", True): ["mono_linux_x86_64.zip", "mono_linux.x86_64.zip"],
    ("Darwin", False): ["macos.universal.zip", "osx.universal.zip", "osx.64.zip"],
    ("Darwin", True): ["mono_macos.universal.zip", "mono_osx.universal.zip"],
}


def _get_session(github_token: Optional[str] = None) -> requests.Session:
    session = requests.Session()
    session.headers["Accept"] = "application/vnd.github+json"
    session.headers["User-Agent"] = "godot-installer/1.0"
    if github_token:
        session.headers["Authorization"] = f"Bearer {github_token}"
    return session


def _is_stable(tag: str) -> bool:
    return bool(re.match(r"^\d+\.\d+(\.\d+)?-stable$", tag))


def _is_prerelease(tag: str) -> bool:
    return bool(re.match(r"^\d+\.\d+(\.\d+)?-(alpha|beta|rc|dev)\d*$", tag))


def _version_sort_key(tag: str) -> tuple:
    """Sort versions numerically."""
    clean = re.sub(r"-(stable|alpha|beta|rc|dev)\d*$", "", tag)
    parts = clean.split(".")
    nums = []
    for p in parts:
        try:
            nums.append(int(p))
        except ValueError:
            nums.append(0)
    # Stable sorts after pre-release
    if "stable" in tag:
        priority = 4
    elif "rc" in tag:
        priority = 3
    elif "beta" in tag:
        priority = 2
    elif "alpha" in tag:
        priority = 1
    else:
        priority = 0
    return (*nums, priority)


class GodotRelease:
    """Represents a single Godot release from GitHub."""

    def __init__(self, tag: str, assets: list[dict], prerelease: bool):
        self.tag = tag
        self.version = tag.replace("-stable", "")
        self.assets = assets
        self.prerelease = prerelease
        self.is_stable = _is_stable(tag)

    def find_asset(self, mono: bool = False) -> Optional[dict]:
        """Find the download asset matching the current platform."""
        system = platform.system()
        patterns = _PLATFORM_PATTERNS.get((system, mono), [])
        for pattern in patterns:
            for asset in self.assets:
                if pattern in asset["name"].lower():
                    return asset
                # Godot 4.x uses different naming
                if pattern.replace(".", "_") in asset["name"].lower():
                    return asset
        # Fallback: try broader matching
        for asset in self.assets:
            name = asset["name"].lower()
            if mono and "mono" not in name:
                continue
            if not mono and "mono" in name:
                continue
            if system == "Windows" and ("win" in name and name.endswith(".zip")):
                return asset
            if system == "Linux" and ("linux" in name and name.endswith(".zip")):
                return asset
            if system == "Darwin" and (("macos" in name or "osx" in name) and name.endswith(".zip")):
                return asset
        return None

    def __repr__(self) -> str:
        label = "stable" if self.is_stable else "pre-release"
        return f"GodotRelease({self.version}, {label})"


def fetch_releases(
    include_prerelease: bool = False,
    github_token: Optional[str] = None,
    limit: int = 50,
) -> list[GodotRelease]:
    """Fetch available Godot releases from GitHub."""
    session = _get_session(github_token)
    releases: list[GodotRelease] = []

    # godot-builds has both stable + pre-release; main repo only stable
    # Fetch from builds repo first (has everything), then fill from main
    repos = [GODOT_BUILDS_REPO, GODOT_REPO]

    for repo in repos:
        page = 1
        fetched_from_repo = 0
        max_per_repo = 60
        while fetched_from_repo < max_per_repo:
            url = f"{GITHUB_API}/repos/{repo}/releases"
            resp = session.get(url, params={"per_page": 30, "page": page})
            if resp.status_code != 200:
                break
            data = resp.json()
            if not data:
                break
            for rel in data:
                tag = rel.get("tag_name", "")
                if not tag:
                    continue
                is_pre = rel.get("prerelease", False)
                if not include_prerelease and is_pre:
                    continue
                assets = [
                    {"name": a["name"], "url": a["browser_download_url"], "size": a["size"]}
                    for a in rel.get("assets", [])
                ]
                if assets:
                    releases.append(GodotRelease(tag, assets, is_pre))
                    fetched_from_repo += 1
            page += 1
            if len(data) < 30:
                break

    # Deduplicate by tag, preferring first occurrence (godot-builds)
    seen = set()
    unique = []
    for r in releases:
        if r.tag not in seen:
            seen.add(r.tag)
            unique.append(r)
    unique.sort(key=lambda r: _version_sort_key(r.tag), reverse=True)
    return unique[:limit]


def fetch_latest_stable(github_token: Optional[str] = None) -> Optional[GodotRelease]:
    """Get the latest stable release."""
    releases = fetch_releases(include_prerelease=False, github_token=github_token, limit=10)
    for r in releases:
        if r.is_stable:
            return r
    return releases[0] if releases else None


def download_godot(
    release: GodotRelease,
    mono: bool = False,
    progress_callback=None,
    github_token: Optional[str] = None,
) -> Path:
    """Download a Godot release and extract it to the versions directory."""
    asset = release.find_asset(mono)
    if not asset:
        system = platform.system()
        raise RuntimeError(
            f"No compatible asset found for {system} in release {release.tag}. "
            f"Available: {[a['name'] for a in release.assets]}"
        )

    cache_dir = get_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / asset["name"]

    # Download if not cached
    if not cache_file.exists():
        session = _get_session(github_token)
        resp = session.get(asset["url"], stream=True)
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))
        downloaded = 0

        with open(cache_file, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if progress_callback and total:
                    progress_callback(downloaded, total)

    # Extract
    suffix = "mono" if mono else "standard"
    version_dir = get_versions_dir() / f"{release.version}-{suffix}"
    if version_dir.exists():
        shutil.rmtree(version_dir)
    version_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(cache_file, "r") as zf:
        zf.extractall(version_dir)

    return version_dir


def get_installed_versions() -> list[dict]:
    """List locally installed Godot versions."""
    versions_dir = get_versions_dir()
    if not versions_dir.exists():
        return []

    installed = []
    for d in sorted(versions_dir.iterdir()):
        if d.is_dir():
            exe = find_godot_executable(d)
            installed.append({
                "version": d.name,
                "path": str(d),
                "executable": str(exe) if exe else None,
            })
    return installed


def find_godot_executable(version_dir: Path) -> Optional[Path]:
    """Find the Godot executable within an extracted version directory."""
    system = platform.system()

    # Search patterns
    if system == "Windows":
        patterns = ["**/*.exe"]
    elif system == "Darwin":
        patterns = ["**/*.app/Contents/MacOS/Godot", "**/*.app"]
    else:
        patterns = ["**/Godot_*", "**/godot.*"]

    for pattern in patterns:
        matches = list(version_dir.glob(pattern))
        for m in matches:
            name = m.name.lower()
            if "console" in name:
                continue
            if m.is_file() or (system == "Darwin" and m.suffix == ".app"):
                return m

    # Fallback: any executable file
    for f in version_dir.rglob("*"):
        if f.is_file() and f.stat().st_mode & 0o111:
            if "godot" in f.name.lower():
                return f

    return None


def remove_version(version_name: str) -> bool:
    """Remove an installed version."""
    version_dir = get_versions_dir() / version_name
    if version_dir.exists():
        shutil.rmtree(version_dir)
        return True
    return False
