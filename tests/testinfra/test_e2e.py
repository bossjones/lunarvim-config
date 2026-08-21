"""Smoke end-to-end Docker asset checks."""

from __future__ import annotations

import json

import pytest


def _run_smoke(host, fixture: str):
    result = host.run(
        "cd /root/lunarvim-config && "
        f"uv run script/smoke.py --mode e2e --only '{fixture}' --json"
    )
    report = json.loads(result.stdout)
    fixture_report = report["results"][0]
    checks = {check["name"]: check for check in fixture_report["checks"]}
    return result, fixture_report, checks


def _run_smoke_without_shfmt(host, mode: str):
    formatter = "/root/.local/share/lvim/mason/bin/shfmt"
    hidden_formatter = formatter + ".smoke-test-hidden"
    moved = host.run(f"mv {formatter} {hidden_formatter}")
    assert moved.rc == 0, moved.stderr
    try:
        result = host.run(
            "cd /root/lunarvim-config && "
            "/usr/local/bin/uv run script/smoke.py "
            "--lvim /root/.local/bin/lvim "
            f"--mode {mode} --only 'shell/script.sh' --json"
        )
        report = json.loads(result.stdout)
        checks = {check["name"]: check for check in report["results"][0]["checks"]}
        return result, checks
    finally:
        restored = host.run(f"mv {hidden_formatter} {formatter}")
        assert restored.rc == 0, restored.stderr


def _run_runner_at_version(host, fixture: str, version: tuple[int, int, int]):
    major, minor, patch = version
    result = host.run(
        "cd /root/lunarvim-config && "
        "/root/.local/bin/lvim --headless "
        f"""-c "lua SMOKE_ROOT='tests/smoke/fixtures'; SMOKE_OUT='/dev/stdout'; """
        f"""SMOKE_MODE='e2e'; SMOKE_ONLY='{fixture}'; """
        f"""vim.version=function() return {{major={major},minor={minor},patch={patch}}} end" """
        "-c 'luafile tests/smoke/runner.lua' -c 'qa!'"
    )
    report_start = result.stdout.find('{"results":')
    assert report_start >= 0, result.stdout
    report, _ = json.JSONDecoder().raw_decode(result.stdout[report_start:])
    checks = {check["name"]: check for check in report["results"][0]["checks"]}
    return report, checks


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


def test_e2e_just_fixture_is_skipped_for_its_neovim_version_range(host):
    result, fixture, checks = _run_smoke(host, "just/justfile")

    assert result.rc == 0, result.stderr
    assert fixture["path"] == "just/justfile"
    assert set(checks) == {"version"}
    assert checks["version"]["status"] == "skip"
    assert checks["version"]["message"] == "nvim version 0.9.5 is below minimum 0.10"


def test_just_fixture_proceeds_at_its_minimum_neovim_version(host):
    report, checks = _run_runner_at_version(host, "just/justfile", (0, 10, 0))

    assert report["nvim"] == "0.10.0"
    assert "version" not in checks
    assert checks["opens"]["status"] == "pass"


def test_e2e_zsh_fixture_does_not_format_outside_format_on_save_patterns(host):
    result, fixture, checks = _run_smoke(host, "shell/.zshrc")

    assert result.rc == 0, result.stderr
    assert fixture["path"] == "shell/.zshrc"
    assert "format" not in checks


@pytest.mark.parametrize(
    ("mode", "returncode", "status"),
    [
        ("smoke", 0, "skip"),
        ("e2e", 1, "fail"),
    ],
)
def test_formatter_availability_has_mode_specific_policy(host, mode: str, returncode: int, status: str):
    result, checks = _run_smoke_without_shfmt(host, mode)

    assert result.rc == returncode, result.stderr
    assert checks["format"]["status"] == status
    assert checks["format"]["message"] == "formatter=shfmt unavailable: shfmt not installed"


def test_e2e_shell_fixture_opens_and_reports_filetype(host):
    result, fixture, checks = _run_smoke(host, "shell/script.sh")
    assert result.rc == 1, result.stderr
    assert fixture["path"] == "shell/script.sh"
    assert fixture["ft_got"] == "sh"
    assert set(checks) >= {"opens", "filetype", "format"}
    assert checks["opens"]["status"] == "pass"
    assert "readable file loaded into buffer" in checks["opens"]["message"]
    assert "7 lines" in checks["opens"]["message"]
    assert checks["filetype"]["status"] == "pass"
    assert "baseline_match=" in checks["format"]["message"]
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
