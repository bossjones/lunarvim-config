"""Smoke end-to-end Docker asset checks."""

from __future__ import annotations

import json


def test_smoke_assets_exist_in_image(host):
    assert host.file(
        "/root/lunarvim-config/tests/smoke/fixtures/log/app.log"
    ).exists


def test_e2e_shell_fixture_opens_and_reports_filetype(host):
    result = host.run(
        "cd /root/lunarvim-config && "
        "uv run script/smoke.py --mode e2e --only 'shell/script.sh' --json"
    )
    report = json.loads(result.stdout)
    fixture = report["results"][0]
    assert result.rc == 0, result.stderr
    assert fixture["path"] == "shell/script.sh"
    assert fixture["ft_got"] == "sh"
    assert {check["name"] for check in fixture["checks"]} >= {"opens", "filetype"}
