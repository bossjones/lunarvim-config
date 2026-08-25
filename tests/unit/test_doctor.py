"""Fast unit tests for the version checks in script/doctor.py.

Everything here is pure parsing or a monkeypatched helper, so no test shells out to
git/nvim or reads the real $HOME. See the plan in specs/ for why these checks exist:
LunarVim's snapshots/default.json pins none-ls to a revision that crashes on Neovim
0.11, and doctor is what surfaces the drift between that pin and config.lua's.
"""

from __future__ import annotations

from pathlib import Path


# ---------------------------------------------------------------------------
# _parse_nvim_version
# ---------------------------------------------------------------------------

def test_parse_nvim_version_reads_first_line(doctor):
    text = "NVIM v0.11.3\nBuild type: Release\nLuaJIT 2.1.1753364724\n"
    assert doctor._parse_nvim_version(text) == (0, 11, 3)


def test_parse_nvim_version_handles_docker_pin(doctor):
    assert doctor._parse_nvim_version("NVIM v0.9.5\n") == (0, 9, 5)


def test_parse_nvim_version_ignores_prerelease_suffix(doctor):
    assert doctor._parse_nvim_version("NVIM v0.12.0-dev-1234+gabcdef\n") == (0, 12, 0)


def test_parse_nvim_version_returns_none_on_garbage(doctor):
    assert doctor._parse_nvim_version("") is None
    assert doctor._parse_nvim_version("not a version string") is None


# ---------------------------------------------------------------------------
# _parse_none_ls_pin
# ---------------------------------------------------------------------------

MULTILINE_SPEC = """
lvim.plugins = {
  { "jose-elias-alvarez/null-ls.nvim", enabled = false },
  {
    "nvimtools/none-ls.nvim",
    -- a comment mentioning commit = "deadbeef" should not confuse us
    commit = "c4b82bb63b13856ba4d6b971b7aad3bb38fc6fe2",
    lazy = true,
    dependencies = { "nvim-lua/plenary.nvim" },
  },
  { "stevearc/dressing.nvim", commit = "1111111" },
}
"""

UNPINNED_SPEC = """
lvim.plugins = {
  { "nvimtools/none-ls.nvim", lazy = true, dependencies = { "nvim-lua/plenary.nvim" } },
  { "stevearc/dressing.nvim", commit = "1111111" },
}
"""


def test_parse_none_ls_pin_finds_multiline_commit(doctor):
    assert (
        doctor._parse_none_ls_pin(MULTILINE_SPEC)
        == "c4b82bb63b13856ba4d6b971b7aad3bb38fc6fe2"
    )


def test_parse_none_ls_pin_returns_none_when_unpinned(doctor):
    """An unpinned none-ls must NOT pick up the next plugin's commit."""
    assert doctor._parse_none_ls_pin(UNPINNED_SPEC) is None


def test_parse_none_ls_pin_returns_none_when_absent(doctor):
    assert doctor._parse_none_ls_pin("lvim.plugins = {}\n") is None


def test_parse_none_ls_pin_matches_repo_config(doctor):
    """The real config.lua must carry an explicit none-ls pin."""
    repo = Path(__file__).resolve().parents[2]
    pin = doctor._parse_none_ls_pin((repo / "config.lua").read_text(encoding="utf-8"))
    assert pin is not None, "config.lua must pin none-ls (LunarVim's snapshot pin crashes on 0.11)"
    assert len(pin) == 40, f"pin should be a full 40-char SHA, got {pin!r}"
    assert not pin.startswith("3a48266"), "config.lua still carries the broken snapshot pin"


# ---------------------------------------------------------------------------
# _lvim_runtime_dir
# ---------------------------------------------------------------------------

def test_lvim_runtime_dir_honors_env(doctor, monkeypatch, tmp_path):
    monkeypatch.setenv("LUNARVIM_RUNTIME_DIR", str(tmp_path / "rt"))
    assert doctor._lvim_runtime_dir() == tmp_path / "rt"


def test_lvim_runtime_dir_defaults_under_home(doctor, monkeypatch):
    monkeypatch.delenv("LUNARVIM_RUNTIME_DIR", raising=False)
    assert doctor._lvim_runtime_dir() == Path.home() / ".local" / "share" / "lunarvim"


# ---------------------------------------------------------------------------
# check_versions
# ---------------------------------------------------------------------------

def _by_name(results, name):
    for r in results:
        if r.name == name:
            return r
    raise AssertionError(f"no check named {name!r} in {[r.name for r in results]}")


def _stub(doctor, monkeypatch, *, nvim, branch, tag, installed):
    monkeypatch.setattr(doctor, "_nvim_version", lambda: nvim)
    monkeypatch.setattr(doctor, "_lvim_git_info", lambda: (branch, tag))
    monkeypatch.setattr(doctor, "_none_ls_installed_commit", lambda: installed)


def test_check_versions_ok_on_supported_nvim(doctor, monkeypatch, tmp_path):
    (tmp_path / "config.lua").write_text(MULTILINE_SPEC, encoding="utf-8")
    _stub(
        doctor, monkeypatch,
        nvim=(0, 11, 3),
        branch=doctor.EXPECTED_LVIM_BRANCH,
        tag="1.4.0",
        installed="c4b82bb63b13856ba4d6b971b7aad3bb38fc6fe2",
    )
    results = doctor.check_versions(tmp_path)
    assert _by_name(results, "Neovim").status is doctor.Status.OK
    assert _by_name(results, "LunarVim").status is doctor.Status.OK
    assert _by_name(results, "none-ls revision").status is doctor.Status.OK


def test_check_versions_errors_below_minimum_nvim(doctor, monkeypatch, tmp_path):
    (tmp_path / "config.lua").write_text(MULTILINE_SPEC, encoding="utf-8")
    _stub(
        doctor, monkeypatch,
        nvim=(0, 8, 3),
        branch=doctor.EXPECTED_LVIM_BRANCH,
        tag="1.4.0",
        installed="c4b82bb63b13856ba4d6b971b7aad3bb38fc6fe2",
    )
    nvim_check = _by_name(doctor.check_versions(tmp_path), "Neovim")
    assert nvim_check.status is doctor.Status.ERROR
    assert nvim_check.severity is doctor.Severity.REQUIRED


def test_check_versions_ok_at_exact_minimum_nvim(doctor, monkeypatch, tmp_path):
    (tmp_path / "config.lua").write_text(MULTILINE_SPEC, encoding="utf-8")
    _stub(
        doctor, monkeypatch,
        nvim=doctor.MIN_NVIM_VERSION,
        branch=doctor.EXPECTED_LVIM_BRANCH,
        tag="1.4.0",
        installed="c4b82bb63b13856ba4d6b971b7aad3bb38fc6fe2",
    )
    assert _by_name(doctor.check_versions(tmp_path), "Neovim").status is doctor.Status.OK


def test_check_versions_warns_on_unexpected_lvim_branch(doctor, monkeypatch, tmp_path):
    (tmp_path / "config.lua").write_text(MULTILINE_SPEC, encoding="utf-8")
    _stub(
        doctor, monkeypatch,
        nvim=(0, 11, 3),
        branch="release-1.3/neovim-0.9",
        tag="1.3.0",
        installed="c4b82bb63b13856ba4d6b971b7aad3bb38fc6fe2",
    )
    lvim_check = _by_name(doctor.check_versions(tmp_path), "LunarVim")
    assert lvim_check.status is doctor.Status.WARN
    assert doctor.EXPECTED_LVIM_BRANCH in lvim_check.message


def test_check_versions_warns_when_none_ls_does_not_match_pin(doctor, monkeypatch, tmp_path):
    """The snapshot pin winning over config.lua is exactly the 0.11 crash."""
    (tmp_path / "config.lua").write_text(MULTILINE_SPEC, encoding="utf-8")
    _stub(
        doctor, monkeypatch,
        nvim=(0, 11, 3),
        branch=doctor.EXPECTED_LVIM_BRANCH,
        tag="1.4.0",
        installed="3a4826687da4310af379515086d71faca4d21288",
    )
    check = _by_name(doctor.check_versions(tmp_path), "none-ls revision")
    assert check.status is doctor.Status.WARN
    assert "plugins-update" in check.fix_hint


def test_check_versions_survives_missing_tools(doctor, monkeypatch, tmp_path):
    """doctor must degrade to a report, never raise, when nvim/lvim are absent."""
    (tmp_path / "config.lua").write_text(UNPINNED_SPEC, encoding="utf-8")
    _stub(doctor, monkeypatch, nvim=None, branch=None, tag=None, installed=None)
    results = doctor.check_versions(tmp_path)
    assert _by_name(results, "Neovim").status is doctor.Status.ERROR
    assert _by_name(results, "LunarVim").status is doctor.Status.WARN


def test_check_versions_registered_in_build_checks(doctor):
    """A check nobody calls is not a check."""
    import inspect
    src = inspect.getsource(doctor.build_checks)
    assert "check_versions" in src
