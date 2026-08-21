"""Fast unit tests for script/smoke.py."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def write_lvim_stub(tmp_path: Path, report: dict[str, object]) -> Path:
    stub = tmp_path / "lvim"
    stub.write_text(
        "#!/usr/bin/env python3\n"
        "import json, re, sys\n"
        "command = next(arg for arg in sys.argv if 'SMOKE_OUT=' in arg)\n"
        "match = re.search(r\"SMOKE_OUT=['\\\"]?([^;'\\\"]+)\", command)\n"
        "assert match, command\n"
        f"with open(match.group(1), 'w', encoding='utf-8') as fh: json.dump({report!r}, fh)\n",
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
