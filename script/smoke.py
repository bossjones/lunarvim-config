#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["rich>=13.0"]
# ///
"""Run the public LunarVim smoke CLI contract."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import uuid
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


FIXTURES_DIR = _repo_root() / "tests" / "smoke" / "fixtures"
RUNNER = _repo_root() / "tests" / "smoke" / "runner.lua"
WORK_DIR = _repo_root() / ".smoke-work"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lvim", default="lvim", help="Path to the LunarVim executable.")
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
) -> list[str]:
    command = f"lua SMOKE_ROOT={str(fixture_root)!r}; SMOKE_OUT={str(report_path)!r}"
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


def load_report(report_path: Path) -> dict[str, object]:
    with report_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def report_exit_code(report: dict[str, object]) -> int:
    if report.get("runner_error"):
        return 1

    for result in report.get("results", []):
        checks = result.get("checks", []) if isinstance(result, dict) else []
        for check in checks:
            if isinstance(check, dict) and check.get("status") == "fail":
                return 1
    return 0


def _make_run_root() -> Path:
    root = WORK_DIR / f"lvim-smoke-{uuid.uuid4().hex}"
    root.mkdir(parents=True, exist_ok=False)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = _make_run_root()
    try:
        fixture_root = stage_fixtures(FIXTURES_DIR, root)
        report_path = root / "report.json"
        subprocess.run(
            build_lvim_command(Path(args.lvim), RUNNER, fixture_root, report_path),
            capture_output=True,
            text=True,
            check=False,
        )
        report = load_report(report_path)
        if args.json:
            print(json.dumps(report, sort_keys=True))
        return report_exit_code(report)
    finally:
        shutil.rmtree(root, ignore_errors=True)
        try:
            WORK_DIR.rmdir()
        except OSError:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
