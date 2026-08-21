"""Fast unit tests for script/smoke.py."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def write_lvim_stub(
    tmp_path: Path,
    report: dict[str, object],
    *,
    include_smoke_root: bool = False,
) -> Path:
    stub = tmp_path / "lvim"
    stub.write_text(
        "#!/usr/bin/env python3\n"
        "import json, re, sys\n"
        "command = next(arg for arg in sys.argv if 'SMOKE_OUT=' in arg)\n"
        "out_match = re.search(r\"SMOKE_OUT=['\\\"]?([^;'\\\"]+)\", command)\n"
        "assert out_match, command\n"
        f"report = {report!r}\n"
        + (
            "root_match = re.search(r\"SMOKE_ROOT=['\\\"]?([^;'\\\"]+)\", command)\n"
            "assert root_match, command\n"
            "report['run_root'] = str(__import__('pathlib').Path(root_match.group(1)).parent)\n"
            if include_smoke_root
            else ""
        )
        + "with open(out_match.group(1), 'w', encoding='utf-8') as fh: json.dump(report, fh)\n",
        encoding="utf-8",
    )
    stub.chmod(0o755)
    return stub


def test_cli_prints_passing_json_report_from_lvim(tmp_path: Path):
    lvim = write_lvim_stub(
        tmp_path,
        {
            "results": [
                {
                    "path": "shell/script.sh",
                    "checks": [
                        {"name": "opens", "status": "pass", "message": ""},
                    ],
                }
            ]
        },
    )

    result = subprocess.run(
        ["uv", "run", "script/smoke.py", "--lvim", str(lvim), "--json"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["results"][0]["path"] == "shell/script.sh"


def test_cli_stages_run_root_in_os_temp_dir(tmp_path: Path):
    lvim = write_lvim_stub(
        tmp_path,
        {
            "results": [
                {
                    "path": "shell/script.sh",
                    "checks": [
                        {"name": "opens", "status": "pass", "message": ""},
                    ],
                }
            ]
        },
        include_smoke_root=True,
    )

    result = subprocess.run(
        ["uv", "run", "script/smoke.py", "--lvim", str(lvim), "--json"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    run_root = Path(json.loads(result.stdout)["run_root"]).resolve()
    assert run_root.parent == Path(tempfile.gettempdir()).resolve()
