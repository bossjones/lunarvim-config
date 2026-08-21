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
    checks = {check["name"]: check for check in fixture["checks"]}
    assert result.rc == 0, result.stderr
    assert fixture["path"] == "shell/script.sh"
    assert fixture["ft_got"] == "sh"
    assert set(checks) >= {"opens", "filetype"}
    assert checks["opens"]["status"] == "pass"
    assert "readable file loaded into buffer" in checks["opens"]["message"]
    assert "5 lines" in checks["opens"]["message"]
    assert checks["filetype"]["status"] == "pass"


def test_e2e_reports_treesitter_and_builtin_syntax(host):
    result = host.run(
        "cd /root/lunarvim-config && "
        "uv run script/smoke.py --mode e2e --only 'xml/Info.plist' --json"
    )
    report = json.loads(result.stdout)
    checks = {c["name"]: c for c in report["results"][0]["checks"]}
    assert result.rc == 0, result.stderr
    assert checks["highlight"]["status"] == "pass"


def test_e2e_reports_treesitter_highlight_for_shell_fixture(host):
    result = host.run(
        "cd /root/lunarvim-config && "
        "uv run script/smoke.py --mode e2e --only 'shell/script.sh' --json"
    )
    report = json.loads(result.stdout)
    checks = {c["name"]: c for c in report["results"][0]["checks"]}
    assert result.rc == 0, result.stderr
    assert checks["highlight"]["status"] == "pass"


def test_e2e_shell_fixture_attaches_and_keeps_lsp_healthy(host):
    result = host.run(
        "cd /root/lunarvim-config && "
        "uv run script/smoke.py --mode e2e --only 'shell/script.sh' --json"
    )
    report = json.loads(result.stdout)
    checks = {check["name"]: check for check in report["results"][0]["checks"]}
    assert result.rc == 0, result.stderr
    assert checks["lsp"]["status"] == "pass"
    assert checks["lsp_healthy"]["status"] == "pass"


def test_e2e_shell_fixture_runs_edit_and_format_checks(host):
    result = host.run(
        "cd /root/lunarvim-config && "
        "uv run script/smoke.py --mode e2e --only 'shell/script.sh' --json"
    )
    report = json.loads(result.stdout)
    checks = {check["name"]: check for check in report["results"][0]["checks"]}
    assert result.rc == 0, result.stderr
    assert checks["edit"]["status"] == "pass"
    assert checks["format"]["status"] == "pass"


def test_e2e_lua_fixture_runs_edit_and_format_checks(host):
    result = host.run(
        "cd /root/lunarvim-config && "
        "uv run script/smoke.py --mode e2e --only 'lua/init.lua' --json"
    )
    report = json.loads(result.stdout)
    checks = {check["name"]: check for check in report["results"][0]["checks"]}
    assert result.rc == 0, result.stderr
    assert checks["edit"]["status"] == "pass"
    assert checks["format"]["status"] == "pass"
