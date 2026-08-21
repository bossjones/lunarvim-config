"""Smoke end-to-end Docker asset checks."""

from __future__ import annotations

import json


def _run_smoke(host, fixture: str):
    result = host.run(
        "cd /root/lunarvim-config && "
        f"uv run script/smoke.py --mode e2e --only '{fixture}' --json"
    )
    report = json.loads(result.stdout)
    fixture_report = report["results"][0]
    checks = {check["name"]: check for check in fixture_report["checks"]}
    return result, fixture_report, checks


def _assert_none_ls_format_failure(checks):
    assert checks["format"]["status"] == "fail"
    assert "client=" in checks["format"]["message"]
    assert "bad argument #2 to 'str_utfindex'" in checks["format"]["message"]


def test_smoke_assets_exist_in_image(host):
    assert host.file(
        "/root/lunarvim-config/tests/smoke/fixtures/log/app.log"
    ).exists


def test_e2e_log_fixture_reports_current_filetype_regression(host):
    result = host.run(
        "cd /root/lunarvim-config && "
        "uv run script/smoke.py --mode e2e --only 'log/app.log' --json"
    )
    report = json.loads(result.stdout)
    checks = {c["name"]: c for c in report["results"][0]["checks"]}
    assert result.rc == 1
    assert checks["filetype"]["status"] == "fail"
    assert "expected log" in checks["filetype"]["message"]


def test_e2e_shell_fixture_opens_and_reports_filetype(host):
    result, fixture, checks = _run_smoke(host, "shell/script.sh")
    assert result.rc == 1, result.stderr
    assert fixture["path"] == "shell/script.sh"
    assert fixture["ft_got"] == "sh"
    assert set(checks) >= {"opens", "filetype", "format"}
    assert checks["opens"]["status"] == "pass"
    assert "readable file loaded into buffer" in checks["opens"]["message"]
    assert "5 lines" in checks["opens"]["message"]
    assert checks["filetype"]["status"] == "pass"
    _assert_none_ls_format_failure(checks)


def test_e2e_reports_treesitter_and_builtin_syntax(host):
    result, _fixture, checks = _run_smoke(host, "xml/Info.plist")
    assert result.rc == 0, result.stderr
    assert checks["highlight"]["status"] == "pass"


def test_e2e_reports_treesitter_highlight_for_shell_fixture(host):
    result, _fixture, checks = _run_smoke(host, "shell/script.sh")
    assert result.rc == 1, result.stderr
    assert checks["highlight"]["status"] == "pass"
    _assert_none_ls_format_failure(checks)


def test_e2e_shell_fixture_attaches_and_keeps_lsp_healthy(host):
    result, _fixture, checks = _run_smoke(host, "shell/script.sh")
    assert result.rc == 1, result.stderr
    assert checks["lsp"]["status"] == "pass"
    assert checks["lsp_healthy"]["status"] == "pass"
    _assert_none_ls_format_failure(checks)


def test_e2e_shell_fixture_reports_edit_pass_and_none_ls_format_failure(host):
    result, _fixture, checks = _run_smoke(host, "shell/script.sh")
    assert result.rc == 1, result.stderr
    assert checks["edit"]["status"] == "pass"
    _assert_none_ls_format_failure(checks)


def test_e2e_lua_fixture_reports_runtime_failures(host):
    result, fixture, checks = _run_smoke(host, "lua/init.lua")
    assert result.rc == 1, result.stderr
    assert fixture["ft_got"] == "lua"
    assert checks["opens"]["status"] == "fail"
    assert "runtime error during open" in checks["opens"]["message"]
    assert "invalid node type at position 2007 for language lua" in checks["opens"]["message"]
    assert checks["highlight"]["status"] == "fail"
    assert checks["highlight"]["message"].startswith("runtime error:")
    assert "\nmessages:\n" in checks["highlight"]["message"]
    assert "query: invalid node type at position 2007 for language lua" in checks["highlight"]["message"]
    assert "invalid node type at position 2007 for language lua" in checks["highlight"]["message"]
    assert checks["edit"]["status"] == "pass"
    _assert_none_ls_format_failure(checks)
