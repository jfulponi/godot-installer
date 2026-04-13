"""CLI interface for Godot Installer."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, BarColumn, DownloadColumn, TransferSpeedColumn
from rich import print as rprint

from . import __version__
from .config import load_config, save_config, get_github_token
from .versions import (
    fetch_releases,
    fetch_latest_stable,
    download_godot,
    get_installed_versions,
    find_godot_executable,
    remove_version,
)
from .shortcuts import create_shortcut, remove_shortcut
from .paths import get_versions_dir

console = Console()


def main():
    parser = argparse.ArgumentParser(
        prog="godot-installer",
        description="Godot Engine version manager and installer",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    sub = parser.add_subparsers(dest="command", help="Available commands")

    # --- list ---
    p_list = sub.add_parser("list", aliases=["ls"], help="List available Godot versions")
    p_list.add_argument("--all", "-a", action="store_true", help="Include pre-release versions")
    p_list.add_argument("--installed", "-i", action="store_true", help="Show only installed versions")
    p_list.add_argument("--limit", "-n", type=int, default=20, help="Max versions to show")

    # --- install ---
    p_install = sub.add_parser("install", aliases=["i"], help="Download and install a Godot version")
    p_install.add_argument("version", nargs="?", help="Version to install (e.g. 4.4, latest)")
    p_install.add_argument("--mono", action="store_true", help="Install Mono/.NET version")
    p_install.add_argument("--no-shortcut", action="store_true", help="Don't create desktop shortcut")

    # --- use ---
    p_use = sub.add_parser("use", help="Set the default Godot version")
    p_use.add_argument("version", help="Version to set as default")

    # --- remove ---
    p_remove = sub.add_parser("remove", aliases=["rm"], help="Remove an installed version")
    p_remove.add_argument("version", help="Version to remove")
    p_remove.add_argument("--keep-shortcut", action="store_true", help="Keep desktop shortcut")

    # --- run ---
    p_run = sub.add_parser("run", help="Launch a Godot version")
    p_run.add_argument("version", nargs="?", help="Version to run (default: current default)")
    p_run.add_argument("args", nargs="*", help="Arguments to pass to Godot")

    # --- shortcut ---
    p_shortcut = sub.add_parser("shortcut", help="Manage desktop shortcuts")
    shortcut_sub = p_shortcut.add_subparsers(dest="shortcut_action")
    p_sc_create = shortcut_sub.add_parser("create", help="Create shortcut for a version")
    p_sc_create.add_argument("version", help="Version to create shortcut for")
    p_sc_remove = shortcut_sub.add_parser("remove", help="Remove shortcut")
    p_sc_remove.add_argument("version", help="Version whose shortcut to remove")

    # --- config ---
    p_config = sub.add_parser("config", help="Manage configuration")
    p_config.add_argument("key", nargs="?", help="Config key to get/set")
    p_config.add_argument("value", nargs="?", help="Value to set")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        commands = {
            "list": cmd_list, "ls": cmd_list,
            "install": cmd_install, "i": cmd_install,
            "use": cmd_use,
            "remove": cmd_remove, "rm": cmd_remove,
            "run": cmd_run,
            "shortcut": cmd_shortcut,
            "config": cmd_config,
        }
        handler = commands.get(args.command)
        if handler:
            handler(args)
        else:
            parser.print_help()
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled.[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


def cmd_list(args):
    config = load_config()
    token = get_github_token(config)

    if args.installed:
        installed = get_installed_versions()
        if not installed:
            console.print("[yellow]No Godot versions installed.[/yellow]")
            console.print("Run [bold]godot-installer install latest[/bold] to get started.")
            return

        table = Table(title="Installed Godot Versions")
        table.add_column("Version", style="cyan")
        table.add_column("Path", style="dim")
        table.add_column("Executable", style="green")

        default = config.get("default_version")
        for v in installed:
            name = v["version"]
            if name == default:
                name = f"{name} [bold yellow](default)[/bold yellow]"
            table.add_row(name, v["path"], v["executable"] or "[red]not found[/red]")

        console.print(table)
        return

    console.print("[dim]Fetching releases from GitHub...[/dim]")
    releases = fetch_releases(
        include_prerelease=args.all,
        github_token=token,
        limit=args.limit,
    )

    if not releases:
        console.print("[yellow]No releases found.[/yellow]")
        return

    installed_names = {v["version"] for v in get_installed_versions()}

    table = Table(title="Available Godot Versions")
    table.add_column("Version", style="cyan")
    table.add_column("Type", style="dim")
    table.add_column("Status")
    table.add_column("Asset")

    for r in releases:
        vtype = "[green]stable[/green]" if r.is_stable else "[yellow]pre-release[/yellow]"
        suffix_standard = f"{r.version}-standard"
        suffix_mono = f"{r.version}-mono"
        if suffix_standard in installed_names or suffix_mono in installed_names:
            status = "[bold green]installed[/bold green]"
        else:
            status = ""
        asset = r.find_asset()
        asset_name = asset["name"] if asset else "[red]no compatible asset[/red]"
        table.add_row(r.version, vtype, status, asset_name)

    console.print(table)


def cmd_install(args):
    config = load_config()
    token = get_github_token(config)
    mono = args.mono or config.get("mono", False)

    version_query = args.version or "latest"

    console.print(f"[dim]Finding Godot version: {version_query}...[/dim]")

    if version_query == "latest":
        release = fetch_latest_stable(github_token=token)
    else:
        releases = fetch_releases(include_prerelease=True, github_token=token, limit=100)
        release = None
        for r in releases:
            if version_query in r.tag or version_query in r.version:
                release = r
                break

    if not release:
        console.print(f"[red]Version '{version_query}' not found.[/red]")
        return

    suffix = "mono" if mono else "standard"
    console.print(f"[bold]Installing Godot {release.version} ({suffix})...[/bold]")

    asset = release.find_asset(mono)
    if asset:
        console.print(f"[dim]Asset: {asset['name']} ({asset['size'] / 1024 / 1024:.1f} MB)[/dim]")

    with Progress(
        "[progress.description]{task.description}",
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Downloading...", total=None)

        def on_progress(downloaded, total):
            progress.update(task, total=total, completed=downloaded)

        version_dir = download_godot(
            release, mono=mono, progress_callback=on_progress, github_token=token,
        )

    exe = find_godot_executable(version_dir)
    if exe:
        console.print(f"[green]Installed to:[/green] {version_dir}")
        console.print(f"[green]Executable:[/green] {exe}")

        # Set as default if it's the only version or no default set
        installed = get_installed_versions()
        if len(installed) == 1 or not config.get("default_version"):
            config["default_version"] = version_dir.name
            save_config(config)
            console.print(f"[cyan]Set as default version.[/cyan]")

        # Create shortcut
        if not args.no_shortcut and config.get("auto_shortcut", True):
            shortcut_name = f"Godot {release.version}"
            if mono:
                shortcut_name += " (Mono)"
            created = create_shortcut(exe, name=shortcut_name)
            for s in created:
                console.print(f"[green]Shortcut created:[/green] {s}")
    else:
        console.print(f"[yellow]Installed to:[/yellow] {version_dir}")
        console.print("[yellow]Warning: Could not find Godot executable in extracted files.[/yellow]")


def cmd_use(args):
    config = load_config()
    installed = get_installed_versions()
    match = None
    for v in installed:
        if args.version in v["version"]:
            match = v
            break

    if not match:
        console.print(f"[red]Version '{args.version}' is not installed.[/red]")
        console.print("Installed versions:")
        for v in installed:
            console.print(f"  {v['version']}")
        return

    config["default_version"] = match["version"]
    save_config(config)
    console.print(f"[green]Default version set to:[/green] {match['version']}")


def cmd_remove(args):
    installed = get_installed_versions()
    match = None
    for v in installed:
        if args.version in v["version"]:
            match = v
            break

    if not match:
        console.print(f"[red]Version '{args.version}' is not installed.[/red]")
        return

    if remove_version(match["version"]):
        console.print(f"[green]Removed:[/green] {match['version']}")

        if not args.keep_shortcut:
            removed = remove_shortcut(f"Godot {match['version'].replace('-standard', '').replace('-mono', ' (Mono)')}")
            for s in removed:
                console.print(f"[dim]Removed shortcut: {s}[/dim]")

        # Update default if we removed it
        config = load_config()
        if config.get("default_version") == match["version"]:
            remaining = get_installed_versions()
            config["default_version"] = remaining[0]["version"] if remaining else None
            save_config(config)
    else:
        console.print(f"[red]Failed to remove {match['version']}.[/red]")


def cmd_run(args):
    config = load_config()
    installed = get_installed_versions()

    if not installed:
        console.print("[red]No Godot versions installed.[/red]")
        console.print("Run [bold]godot-installer install latest[/bold] to get started.")
        return

    version_query = args.version or config.get("default_version")
    if not version_query:
        version_query = installed[0]["version"]

    match = None
    for v in installed:
        if version_query in v["version"]:
            match = v
            break

    if not match or not match["executable"]:
        console.print(f"[red]Cannot find executable for '{version_query}'.[/red]")
        return

    import subprocess
    exe = match["executable"]
    console.print(f"[green]Launching Godot {match['version']}...[/green]")
    subprocess.Popen([exe] + (args.args or []))


def cmd_shortcut(args):
    if not args.shortcut_action:
        console.print("[yellow]Usage: godot-installer shortcut create|remove VERSION[/yellow]")
        return

    installed = get_installed_versions()
    match = None
    for v in installed:
        if args.version in v["version"]:
            match = v
            break

    if not match:
        console.print(f"[red]Version '{args.version}' is not installed.[/red]")
        return

    version_label = match["version"].replace("-standard", "").replace("-mono", " (Mono)")

    if args.shortcut_action == "create":
        exe = match.get("executable")
        if not exe:
            console.print("[red]No executable found for this version.[/red]")
            return
        created = create_shortcut(Path(exe), name=f"Godot {version_label}")
        for s in created:
            console.print(f"[green]Created:[/green] {s}")

    elif args.shortcut_action == "remove":
        removed = remove_shortcut(f"Godot {version_label}")
        if removed:
            for s in removed:
                console.print(f"[green]Removed:[/green] {s}")
        else:
            console.print("[yellow]No shortcuts found to remove.[/yellow]")


def cmd_config(args):
    config = load_config()

    if not args.key:
        table = Table(title="Configuration")
        table.add_column("Key", style="cyan")
        table.add_column("Value")
        for k, v in config.items():
            display = str(v) if v is not None else "[dim]not set[/dim]"
            if k == "github_token" and v:
                display = v[:8] + "..." + v[-4:]
            table.add_row(k, display)
        console.print(table)
        return

    if args.value is None:
        val = config.get(args.key, "[dim]not set[/dim]")
        console.print(f"[cyan]{args.key}:[/cyan] {val}")
    else:
        # Type coercion
        value = args.value
        if value.lower() == "true":
            value = True
        elif value.lower() == "false":
            value = False
        elif value.lower() == "none" or value.lower() == "null":
            value = None

        config[args.key] = value
        save_config(config)
        console.print(f"[green]Set {args.key} = {value}[/green]")


if __name__ == "__main__":
    main()
