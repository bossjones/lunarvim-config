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
from pathlib import Path

from rich.console import Console
from rich.table import Table


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


FIXTURES_DIR = _repo_root() / "tests" / "smoke" / "fixtures"
RUNNER = _repo_root() / "tests" / "smoke" / "runner.lua"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lvim", default="lvim", help="Path to the LunarVim executable.")
    parser.add_argument("--mode", choices=("smoke", "e2e"), default="smoke", help="Smoke policy to enforce.")
    parser.add_argument("--only", default=None, help="Optional fixture glob filter passed to the runner.")
    parser.add_argument("--target", type=Path, default=None, help="Optional LunarVim config directory for the runner.")
    parser.add_argument("--timeout", type=float, default=60.0, help="Seconds to wait for the runner before failing.")
    parser.add_argument("--json", action="store_true", help="Print the JSON report only.")
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


def resolve_lvim(lvim: str) -> Path | None:
    resolved = shutil.which(lvim)
    return Path(resolved) if resolved is not None else None


def load_report(report_path: Path) -> dict[str, object]:
    with report_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


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
            table.add_row(
                path,
                ft_got,
                str(check.get("name", "")),
                str(check.get("status", "")),
                str(check.get("message", "")),
            )

    console.print(table)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    console = Console()
    lvim = resolve_lvim(args.lvim)
    if lvim is None:
        return 2
    try:
        with tempfile.TemporaryDirectory(prefix="lvim-smoke-") as raw_root:
            root = Path(raw_root)
            fixture_root = stage_fixtures(FIXTURES_DIR, root)
            report_path = root / "report.json"
            subprocess.run(
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
            if report_path.exists():
                report = load_report(report_path)
            else:
                report = runner_error_report(f"runner did not produce report: {report_path}")
    except subprocess.TimeoutExpired:
        return 1
    except OSError:
        return 2
    if args.json:
        print(json.dumps(report, sort_keys=True))
    else:
        render_report(report, console)
    return report_exit_code(report, args.mode)


if __name__ == "__main__":
    raise SystemExit(main())
