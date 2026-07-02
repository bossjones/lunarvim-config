#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["rich>=13.0"]
# ///
"""Install the lunarvim-config payload into ~/.config/lvim/.

Usage:
    uv run script/install.py [--dry-run] [--yes] [--target DIR] [--repo DIR] [--no-backup]

Backs up any existing config (zip snapshot to ~/.config/lvim-backups/), moves it aside
to a timestamped directory, then installs the config payload. `--dry-run` previews the
plan and colored diffs without touching the filesystem.

Exit code 0 = success (or dry-run preview).
Exit code 1 = runtime error (missing source items, copy failure).
Exit code 2 = bad arguments (usage error, --repo does not exist).

See specs/install.md for the full contract.
"""

from __future__ import annotations

import argparse
import difflib
import shutil
import sys
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table


# ---------------------------------------------------------------------------
# Manifest — the single source of truth for what gets deployed.
# Mirrors `make sync` MINUS `.git` (a deployed config shouldn't carry the repo's
# git dir; backups already exclude it).
# ---------------------------------------------------------------------------

MANIFEST_FILES: tuple[str, ...] = (
    "Makefile",
    "config.lua",
    "README.md",
    ".luarc.json",
    ".luacheckrc",
    ".markdownlint.json",
    ".stylua.toml",
    ".gitignore",
    "LICENSE",
)

MANIFEST_DIRS: tuple[str, ...] = (
    "lsp-settings",
    "ftplugin",
    "after",
    ".vale",
    "ftdetect",
    "snippets",
    "lua",
)

MANIFEST: tuple[str, ...] = MANIFEST_FILES + MANIFEST_DIRS


# ---------------------------------------------------------------------------
# Data model (mirrors doctor.py conventions)
# ---------------------------------------------------------------------------

class ActionKind(Enum):
    CREATE = "CREATE"
    OVERWRITE = "OVERWRITE"
    UNCHANGED = "UNCHANGED"


@dataclass
class FileAction:
    rel_path: str            # path relative to the target, e.g. "lua/user/init.lua"
    kind: ActionKind
    is_binary: bool = False
    diff: str = ""           # unified diff text for changed text files


@dataclass
class InstallPlan:
    actions: list[FileAction] = field(default_factory=list)
    backup_zip: Path | None = None
    moved_to: Path | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _repo_root() -> Path:
    """Return the repository root (parent of script/)."""
    return Path(__file__).resolve().parent.parent


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def _is_binary(path: Path) -> bool:
    """Heuristic: a file is binary if its first chunk contains a NUL byte."""
    try:
        with path.open("rb") as fh:
            chunk = fh.read(8192)
    except OSError:
        return False
    return b"\x00" in chunk


def _iter_source_files(repo: Path, item: str):
    """Yield (source_path, rel_path) leaf files for a manifest item.

    A file item yields itself; a directory item yields each file beneath it, with
    rel_path relative to the target (i.e. including the item name as prefix).
    """
    src = repo / item
    if src.is_file():
        yield src, item
    elif src.is_dir():
        for p in sorted(src.rglob("*")):
            if p.is_file():
                yield p, str(p.relative_to(repo))


# ---------------------------------------------------------------------------
# Core logic (pure — no reference to real $HOME)
# ---------------------------------------------------------------------------

def build_plan(repo: Path, target: Path) -> InstallPlan:
    """Classify every leaf file that would be installed from `repo` into `target`."""
    actions: list[FileAction] = []

    for item in MANIFEST:
        for src, rel in _iter_source_files(repo, item):
            dest = target / rel
            src_bytes = src.read_bytes()

            if not dest.exists():
                actions.append(FileAction(rel, ActionKind.CREATE, _is_binary(src)))
                continue

            dest_bytes = dest.read_bytes()
            if src_bytes == dest_bytes:
                actions.append(FileAction(rel, ActionKind.UNCHANGED, _is_binary(src)))
                continue

            is_bin = _is_binary(src) or _is_binary(dest)
            diff = "" if is_bin else _unified_diff(dest_bytes, src_bytes, rel)
            actions.append(FileAction(rel, ActionKind.OVERWRITE, is_bin, diff))

    return InstallPlan(actions=actions)


def _unified_diff(old: bytes, new: bytes, rel: str) -> str:
    old_lines = old.decode("utf-8", "replace").splitlines(keepends=True)
    new_lines = new.decode("utf-8", "replace").splitlines(keepends=True)
    return "".join(
        difflib.unified_diff(
            old_lines, new_lines,
            fromfile=f"a/{rel}", tofile=f"b/{rel}",
        )
    )


def backup_existing(
    target: Path, backups_dir: Path, timestamp: str
) -> tuple[Path | None, Path | None]:
    """Zip-snapshot `target` (excluding .git), then move it aside.

    Returns (zip_path, moved_to). Both are None if `target` does not exist.
    """
    if not target.exists():
        return None, None

    backups_dir.mkdir(parents=True, exist_ok=True)
    zip_path = backups_dir / f"lvim-backup-{timestamp}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(target.rglob("*")):
            if p.is_file() and ".git" not in p.relative_to(target).parts:
                arcname = Path(target.name) / p.relative_to(target)
                zf.write(p, arcname.as_posix())

    moved_to = target.parent / f"{target.name}.bak.{timestamp}"
    shutil.move(str(target), str(moved_to))
    return zip_path, moved_to


def apply_plan(repo: Path, target: Path) -> None:
    """Copy every manifest item from `repo` into `target` (skips missing items and .git)."""
    target.mkdir(parents=True, exist_ok=True)
    for item in MANIFEST:
        src = repo / item
        dest = target / item
        if src.is_file():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
        elif src.is_dir():
            shutil.copytree(
                src, dest, dirs_exist_ok=True,
                ignore=shutil.ignore_patterns(".git"),
            )


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

KIND_ICON = {
    ActionKind.CREATE: "[green]+[/]",
    ActionKind.OVERWRITE: "[yellow]~[/]",
    ActionKind.UNCHANGED: "[dim]=[/]",
}

KIND_STYLE = {
    ActionKind.CREATE: "green",
    ActionKind.OVERWRITE: "yellow",
    ActionKind.UNCHANGED: "dim",
}


def render_preview(plan: InstallPlan, target: Path, console: Console) -> None:
    """Print the per-file plan table plus colored diffs for changed files."""
    table = Table(title=f"Install plan → {target}", title_style="bold cyan", pad_edge=False)
    table.add_column("", width=3, justify="center")
    table.add_column("File")
    table.add_column("Action", width=10)

    for a in plan.actions:
        table.add_row(
            KIND_ICON[a.kind],
            a.rel_path + ("  [dim](binary)[/]" if a.is_binary else ""),
            f"[{KIND_STYLE[a.kind]}]{a.kind.value}[/]",
        )
    console.print(table)
    console.print()

    changed = [a for a in plan.actions if a.kind is ActionKind.OVERWRITE and a.diff]
    for a in changed:
        console.print(f"[bold]diff — {a.rel_path}[/]")
        console.print(Syntax(a.diff, "diff", theme="ansi_dark", background_color="default"))
        console.print()


def _counts(plan: InstallPlan) -> tuple[int, int, int]:
    create = sum(1 for a in plan.actions if a.kind is ActionKind.CREATE)
    overwrite = sum(1 for a in plan.actions if a.kind is ActionKind.OVERWRITE)
    unchanged = sum(1 for a in plan.actions if a.kind is ActionKind.UNCHANGED)
    return create, overwrite, unchanged


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="install.py",
        description="Install the lunarvim-config payload into ~/.config/lvim/.",
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview the plan and diffs without modifying anything.")
    parser.add_argument("-y", "--yes", action="store_true",
                        help="Skip the interactive confirmation prompt.")
    parser.add_argument("--target", type=Path, default=None,
                        help="Destination dir (default: ~/.config/lvim).")
    parser.add_argument("--repo", type=Path, default=None,
                        help="Source repo dir (default: this script's repo root).")
    parser.add_argument("--no-backup", action="store_true",
                        help="Skip the zip snapshot and move-aside; overwrite in place.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    console = Console()

    repo = (args.repo or _repo_root()).expanduser()
    target = (args.target or (Path.home() / ".config" / "lvim")).expanduser()
    backups_dir = target.parent / f"{target.name}-backups"

    if not repo.is_dir():
        console.print(f"[bold red]error:[/] --repo path does not exist: {repo}")
        return 2

    # Verify the source actually contains the manifest before doing anything.
    missing = [item for item in MANIFEST if not (repo / item).exists()]
    if missing:
        console.print(f"[bold red]error:[/] repo is missing manifest items: {', '.join(missing)}")
        return 1

    console.print(f"[bold]lunarvim-config installer[/]  —  repo: {repo}\n")

    plan = build_plan(repo, target)
    render_preview(plan, target, console)
    create, overwrite, unchanged = _counts(plan)
    console.print(
        f"[green]create:[/] {create}   [yellow]overwrite:[/] {overwrite}   "
        f"[dim]unchanged:[/] {unchanged}\n"
    )

    if args.dry_run:
        console.print(Panel("Dry run — no changes were made.", border_style="cyan"))
        return 0

    if not args.yes:
        try:
            reply = input(f"Install into {target}? [y/N] ").strip().lower()
        except EOFError:
            reply = ""
        if reply not in ("y", "yes"):
            console.print("[yellow]Aborted.[/]")
            return 0

    try:
        timestamp = _timestamp()
        zip_path: Path | None = None
        moved_to: Path | None = None
        if not args.no_backup:
            zip_path, moved_to = backup_existing(target, backups_dir, timestamp)
        elif target.exists():
            shutil.rmtree(target)
        apply_plan(repo, target)
    except OSError as exc:
        console.print(f"[bold red]install failed:[/] {exc}")
        return 1

    lines = [f"[bold green]Installed to[/] {target}"]
    if zip_path:
        lines.append(f"[dim]Backup zip:[/] {zip_path}")
    if moved_to:
        lines.append(f"[dim]Previous config moved to:[/] {moved_to}")
    console.print(Panel("\n".join(lines), title="Done", border_style="green"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
