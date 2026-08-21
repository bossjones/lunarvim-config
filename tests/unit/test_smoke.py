"""Fast unit tests for script/smoke.py."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest
from rich.console import Console

REPO_ROOT = Path(__file__).resolve().parents[2]


def write_lvim_stub(
    tmp_path: Path,
    report: dict[str, object],
    *,
    include_smoke_root: bool = False,
    write_report: bool = True,
    stderr: str = "",
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
        + (
            "with open(out_match.group(1), 'w', encoding='utf-8') as fh: json.dump(report, fh)\n"
            if write_report
            else ""
        )
        + (f"print({stderr!r}, file=sys.stderr)\n" if stderr else ""),
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


def test_cli_keep_retains_staged_artifacts_and_reports_their_path(tmp_path: Path):
    lvim = write_lvim_stub(
        tmp_path,
        {"results": []},
        include_smoke_root=True,
    )

    result = subprocess.run(
        ["uv", "run", "script/smoke.py", "--lvim", str(lvim), "--keep", "--json"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    run_root = Path(json.loads(result.stdout)["run_root"])
    try:
        assert run_root.exists()
        assert "retained smoke artifacts:" in result.stderr
        assert str(run_root) in result.stderr
    finally:
        shutil.rmtree(run_root, ignore_errors=True)


def test_cli_default_run_removes_staged_artifacts(tmp_path: Path):
    lvim = write_lvim_stub(
        tmp_path,
        {"results": []},
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
    assert not Path(json.loads(result.stdout)["run_root"]).exists()


def test_repository_fixture_files_are_not_ignored():
    fixtures = [
        "tests/smoke/fixtures/log/app.log",
        "tests/smoke/fixtures/ini/settings.ini",
        "tests/smoke/fixtures/shell/.zshrc",
        "tests/smoke/fixtures/git/.gitignore",
        "tests/smoke/fixtures/just/.justfile",
    ]

    result = subprocess.run(
        ["git", "check-ignore", *fixtures],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1, result.stdout


def test_stage_fixtures_preserves_dotfiles(tmp_path: Path, smoke):
    source = tmp_path / "source"
    (source / "ssh" / ".ssh").mkdir(parents=True)
    (source / "ssh" / ".ssh" / "config").write_text("Host smoke\n", encoding="utf-8")
    (source / "shell").mkdir()
    (source / "shell" / ".zshrc").write_text("setopt prompt_subst\n", encoding="utf-8")

    staged = smoke.stage_fixtures(source, tmp_path / "stage")

    assert (staged / "ssh" / ".ssh" / "config").read_text(encoding="utf-8") == "Host smoke\n"
    assert (staged / "shell" / ".zshrc").read_text(encoding="utf-8") == "setopt prompt_subst\n"


def test_e2e_fails_missing_binary_skip_but_smoke_allows_it(smoke):
    report = {
        "results": [
            {
                "checks": [
                    {
                        "name": "lsp",
                        "status": "skip",
                        "message": "bash-language-server not installed",
                    }
                ]
            }
        ]
    }

    assert smoke.report_exit_code(report, "smoke") == 0
    assert smoke.report_exit_code(report, "e2e") == 1


def test_e2e_allows_version_skip(smoke):
    report = {
        "results": [
            {
                "checks": [
                    {
                        "name": "version",
                        "status": "skip",
                        "message": "nvim version 0.9.5 does not support leap.nvim",
                    }
                ]
            }
        ]
    }

    assert smoke.report_exit_code(report, "e2e") == 0


@pytest.mark.parametrize(
    ("report", "mode"),
    [
        ({}, "smoke"),
        ({}, "e2e"),
        ({"results": {"checks": []}}, "smoke"),
        ({"results": {"checks": []}}, "e2e"),
    ],
    ids=["missing-results-smoke", "missing-results-e2e", "non-list-results-smoke", "non-list-results-e2e"],
)
def test_cli_rejects_malformed_runner_reports(
    smoke, tmp_path: Path, capsys, report: object, mode: str
):
    lvim = write_lvim_stub(tmp_path, report)

    assert smoke.main(["--lvim", str(lvim), "--mode", mode]) == 1

    assert "runner report must be a mapping containing a list-valued 'results' field" in capsys.readouterr().out


def test_cli_accepts_valid_empty_runner_report(smoke, tmp_path: Path):
    lvim = write_lvim_stub(tmp_path, {"results": []})

    assert smoke.main(["--lvim", str(lvim)]) == 0


def test_cli_defaults_and_flags_match_public_contract(smoke):
    args = smoke.parse_args([])

    assert args.timeout == 180
    assert args.keep is False
    assert args.verbose is False


def test_default_lvim_resolution_falls_back_to_an_executable_on_path(smoke, monkeypatch, tmp_path: Path):
    home = tmp_path / "home"
    local_lvim = home / ".local" / "bin" / "lvim"
    local_lvim.parent.mkdir(parents=True)
    local_lvim.write_text("#!/bin/sh\n", encoding="utf-8")
    local_lvim.chmod(0o644)
    path_lvim = tmp_path / "bin" / "lvim"
    path_lvim.parent.mkdir()
    path_lvim.write_text("#!/bin/sh\n", encoding="utf-8")
    path_lvim.chmod(0o755)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(smoke.shutil, "which", lambda name: str(path_lvim))

    assert smoke.resolve_lvim(None) == path_lvim


def test_default_lvim_resolution_uses_executable_home_fallback(smoke, monkeypatch, tmp_path: Path):
    home = tmp_path / "home"
    local_lvim = home / ".local" / "bin" / "lvim"
    local_lvim.parent.mkdir(parents=True)
    local_lvim.write_text("#!/bin/sh\n", encoding="utf-8")
    local_lvim.chmod(0o755)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(smoke.shutil, "which", lambda name: None)

    assert smoke.resolve_lvim(None) == local_lvim


def test_cli_reports_clear_error_when_no_executable_is_available(smoke, monkeypatch, tmp_path: Path, capsys):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("PATH", "")

    assert smoke.main([]) == 2

    captured = capsys.readouterr()
    assert "no executable LunarVim found" in captured.out + captured.err


def test_cli_verbose_prints_runner_diagnostics_without_corrupting_json(tmp_path: Path):
    lvim = write_lvim_stub(
        tmp_path,
        {"results": []},
        stderr="runner diagnostic",
    )

    quiet = subprocess.run(
        ["uv", "run", "script/smoke.py", "--lvim", str(lvim), "--json"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    verbose = subprocess.run(
        ["uv", "run", "script/smoke.py", "--lvim", str(lvim), "--verbose", "--json"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert quiet.returncode == verbose.returncode == 0
    assert json.loads(quiet.stdout) == json.loads(verbose.stdout) == {"results": []}
    assert quiet.stderr == ""
    assert "runner diagnostic" in verbose.stderr


def test_build_lvim_command_passes_runner_globals(smoke, tmp_path: Path):
    command = smoke.build_lvim_command(
        tmp_path / "lvim",
        tmp_path / "runner.lua",
        tmp_path / "fixtures",
        tmp_path / "report.json",
        "shell/*",
        mode="e2e",
    )

    lua_command = next(arg for arg in command if "SMOKE_ROOT=" in arg)
    assert "SMOKE_ROOT=" in lua_command
    assert "SMOKE_OUT=" in lua_command
    assert "SMOKE_MODE='e2e'" in lua_command
    assert "SMOKE_ONLY='shell/*'" in lua_command


def test_runner_env_sets_target_only_when_supplied(smoke, monkeypatch, tmp_path: Path):
    monkeypatch.setenv("LUNARVIM_CONFIG_DIR", "/leaked-host-config")

    without_target = smoke.runner_env(None)
    with_target = smoke.runner_env(tmp_path / "target")

    assert "LUNARVIM_CONFIG_DIR" not in without_target
    assert with_target["LUNARVIM_CONFIG_DIR"] == str(tmp_path / "target")


def test_timeout_returns_one(smoke, monkeypatch, tmp_path: Path):
    monkeypatch.setenv("PATH", "")
    lvim = write_lvim_stub(tmp_path, {})

    def timeout(command, *_args, **_kwargs):
        assert command[0] == str(lvim)
        raise subprocess.TimeoutExpired("lvim", 1)

    monkeypatch.setattr(smoke.subprocess, "run", timeout)

    assert smoke.main(["--lvim", str(lvim), "--timeout", "1"]) == 1


def test_missing_report_returns_one(smoke, tmp_path: Path):
    lvim = write_lvim_stub(tmp_path, {}, write_report=False)

    assert smoke.main(["--lvim", str(lvim), "--json"]) == 1


def test_missing_lvim_returns_two(smoke, tmp_path: Path):
    assert smoke.main(["--lvim", str(tmp_path / "missing-lvim")]) == 2


def test_render_report_contains_fixture_and_check_status(smoke):
    console = Console(record=True, width=160)

    smoke.render_report(
        {
            "results": [
                {
                    "path": "shell/script.sh",
                    "ft_got": "sh",
                    "checks": [
                        {"name": "opens", "status": "pass", "message": ""},
                        {
                            "name": "version-gated",
                            "status": "skip",
                            "message": "nvim version 0.9.5 does not support leap.nvim",
                        },
                        {
                            "name": "format",
                            "status": "skip",
                            "message": "shfmt not installed",
                        },
                        {"name": "highlight", "status": "pass", "message": "parser=true highlighter=true"},
                        {"name": "lsp", "status": "fail", "message": "bashls missing"},
                        {"name": "lsp_healthy", "status": "pass", "message": "clients healthy (bashls)"},
                        {"name": "edit", "status": "pass", "message": "insert/undo restored buffer"},
                        {"name": "format", "status": "fail", "message": "formatter=shfmt"},
                    ],
                }
            ]
        },
        console,
    )

    output = console.export_text()
    assert "shell/script.sh" in output
    assert "opens" in output
    assert "version-gated" in output
    assert "highlight" in output
    assert "lsp" in output
    assert "lsp_healthy" in output
    assert "edit" in output
    assert "format" in output
    assert "pass" in output
    assert "skip" in output
    assert "fail" in output
    assert "Skip summary" in output
    assert "version" in output
    assert "availability" in output
