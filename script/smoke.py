#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["rich>=13.0"]
# ///
"""Run the public LunarVim smoke CLI contract."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from collections import Counter
from pathlib import Path

from rich.console import Console
from rich.table import Table


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


FIXTURES_DIR = _repo_root() / "tests" / "smoke" / "fixtures"
RUNNER = _repo_root() / "tests" / "smoke" / "runner.lua"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lvim", default=None, help="Path to the LunarVim executable.")
    parser.add_argument("--mode", choices=("smoke", "e2e"), default="smoke", help="Smoke policy to enforce.")
    parser.add_argument("--only", default=None, help="Optional fixture glob filter passed to the runner.")
    parser.add_argument("--target", type=Path, default=None, help="Optional LunarVim config directory for the runner.")
    parser.add_argument("--timeout", type=float, default=180.0, help="Seconds to wait for the runner before failing.")
    parser.add_argument("--json", action="store_true", help="Print the JSON report only.")
    parser.add_argument("--keep", action="store_true", help="Retain staged smoke artifacts for debugging.")
    parser.add_argument("--verbose", action="store_true", help="Print runner diagnostics to stderr.")
    return parser.parse_args(argv)


def stage_fixtures(fixtures_dir: Path, root: Path) -> Path:
    staged = root / "fixtures"
    shutil.copytree(fixtures_dir, staged)
    return staged


def build_lvim_command(
    lvim: Path,
    runner: Path,
    fixture_root: Path,
    report_path: Path,
    only: str | None = None,
    *,
    mode: str = "smoke",
) -> list[str]:
    only_value = "nil" if only is None else repr(only)
    command = (
        f"lua SMOKE_ROOT={str(fixture_root)!r}; "
        f"SMOKE_OUT={str(report_path)!r}; "
        f"SMOKE_MODE={mode!r}; "
        f"SMOKE_ONLY={only_value}"
    )
    return [
        str(lvim),
        "--headless",
        "-c",
        command,
        "-c",
        f"luafile {runner}",
        "-c",
        "qa!",
    ]


def runner_env(target: Path | None) -> dict[str, str]:
    env = os.environ.copy()
    env.pop("LUNARVIM_CONFIG_DIR", None)
    if target is not None:
        env["LUNARVIM_CONFIG_DIR"] = str(target)
    return env


def _executable_candidate(candidate: str | Path | None) -> Path | None:
    if candidate is None:
        return None
    path = Path(candidate).expanduser()
    if path.is_file() and os.access(path, os.X_OK):
        return path
    return None


def resolve_lvim(lvim: str | None) -> Path | None:
    if lvim is not None:
        return _executable_candidate(shutil.which(lvim) or lvim)

    on_path = _executable_candidate(shutil.which("lvim"))
    if on_path is not None:
        return on_path
    return _executable_candidate(Path.home() / ".local" / "bin" / "lvim")


def load_report(report_path: Path) -> dict[str, object]:
    try:
        with report_path.open("r", encoding="utf-8") as handle:
            report = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"runner report is unreadable: {error}") from error
    if not isinstance(report, dict) or not isinstance(report.get("results"), list):
        raise ValueError("runner report must be a mapping containing a list-valued 'results' field")
    return report


def runner_error_report(message: str) -> dict[str, object]:
    return {"runner_error": message, "results": []}


def is_version_skip(message: str) -> bool:
    return message.startswith("nvim version ")


def report_exit_code(report: dict[str, object], mode: str) -> int:
    if report.get("runner_error"):
        return 1

    for result in report.get("results", []):
        checks = result.get("checks", []) if isinstance(result, dict) else []
        for check in checks:
            if not isinstance(check, dict):
                continue
            if check.get("status") == "fail":
                return 1
            if (
                mode == "e2e"
                and check.get("status") == "skip"
                and not is_version_skip(str(check.get("message", "")))
            ):
                return 1
    return 0


def render_report(report: dict[str, object], console: Console) -> None:
    if report.get("runner_error"):
        console.print(f"[red]{report['runner_error']}[/red]")

    table = Table(title="Smoke report", pad_edge=False)
    table.add_column("Fixture")
    table.add_column("Filetype")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Message")

    skip_categories: Counter[str] = Counter()
    for result in report.get("results", []):
        if not isinstance(result, dict):
            continue
        path = str(result.get("path", ""))
        ft_got = str(result.get("ft_got", ""))
        checks = result.get("checks", [])
        if not checks:
            table.add_row(path, ft_got, "", "", "")
            continue
        for check in checks:
            if not isinstance(check, dict):
                continue
            if check.get("status") == "skip":
                message = str(check.get("message", ""))
                category = "version" if is_version_skip(message) else (
                    "availability" if "not installed" in message else "other"
                )
                skip_categories[category] += 1
            table.add_row(
                path,
                ft_got,
                str(check.get("name", "")),
                str(check.get("status", "")),
                str(check.get("message", "")),
            )

    console.print(table)
    if skip_categories:
        summary = Table(title="Skip summary", pad_edge=False)
        summary.add_column("Category")
        summary.add_column("Skipped checks")
        for category, count in sorted(skip_categories.items()):
            summary.add_row(category, str(count))
        console.print(summary)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    console = Console()
    diagnostics = Console(stderr=True)
    lvim = resolve_lvim(args.lvim)
    if lvim is None:
        diagnostics.print("[red]no executable LunarVim found; pass --lvim PATH or add lvim to PATH[/red]")
        return 2
    root: Path | None = None
    try:
        root = Path(tempfile.mkdtemp(prefix="lvim-smoke-"))
        fixture_root = stage_fixtures(FIXTURES_DIR, root)
        report_path = root / "report.json"
        completed = subprocess.run(
            build_lvim_command(
                lvim,
                RUNNER,
                fixture_root,
                report_path,
                args.only,
                mode=args.mode,
            ),
            capture_output=True,
            text=True,
            check=False,
            env=runner_env(args.target),
            timeout=args.timeout,
        )
        if args.verbose and completed.stderr:
            diagnostics.print(completed.stderr.rstrip())
        try:
            report = load_report(report_path)
        except ValueError as error:
            if completed.stderr and not args.verbose:
                diagnostics.print(completed.stderr.rstrip())
            report = runner_error_report(str(error))
    except subprocess.TimeoutExpired:
        report = runner_error_report("runner hung (likely LSP wait) — rerun with --keep")
    except OSError as error:
        if root is not None:
            shutil.rmtree(root, ignore_errors=True)
        diagnostics.print(f"[red]failed to invoke LunarVim: {error}[/red]")
        return 2
    try:
        if args.json:
            print(json.dumps(report, sort_keys=True))
        else:
            render_report(report, console)
        return report_exit_code(report, args.mode)
    finally:
        if root is not None:
            if args.keep:
                diagnostics.print(f"retained smoke artifacts: {root}")
            else:
                shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
