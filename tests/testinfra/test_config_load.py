"""Assert the LunarVim config loads headlessly without errors."""

from __future__ import annotations

LVIM = "/root/.local/bin/lvim"


def test_headless_config_loads(host):
    cmd = host.run(
        "%s --headless -c \"lua print('config loaded ok')\" -c q", LVIM
    )
    combined = cmd.stdout + cmd.stderr
    assert cmd.rc == 0, f"lvim exited {cmd.rc}\n{combined}"
    assert "config loaded ok" in combined


def test_snacks_loads(host):
    cmd = host.run(
        "%s --headless "
        "-c \"lua print('snacks: ' .. tostring(pcall(require, 'snacks')))\" -c q",
        LVIM,
    )
    combined = cmd.stdout + cmd.stderr
    assert "snacks: true" in combined, combined


def test_no_null_ls_builtin_failures(host):
    """After moving ruff to the native LSP and shellcheck to bashls, null-ls should
    load cleanly with no 'failed to load builtin' warnings on config load."""
    cmd = host.run(
        "%s --headless -c \"lua print('done')\" -c q", LVIM
    )
    combined = cmd.stdout + cmd.stderr
    assert "failed to load builtin" not in combined, combined
    assert "Not a valid source" not in combined, combined


def test_ruff_server_subcommand(host):
    """ruff is configured as a native LSP via `ruff server`."""
    cmd = host.run("ruff server --help")
    assert cmd.rc == 0, f"`ruff server` not available: {cmd.stdout}{cmd.stderr}"


def test_null_ls_available(host):
    """ruff/shfmt/stylua/shellcheck run through null-ls; LunarVim 1.3 pins a dead
    null-ls repo, so config.lua installs the nvimtools/none-ls fork which provides
    the `null-ls` module. Assert it loads."""
    cmd = host.run(
        "%s --headless "
        "-c \"lua print('null_ls: ' .. tostring(pcall(require, 'null-ls')))\" -c q",
        LVIM,
    )
    combined = cmd.stdout + cmd.stderr
    assert "null_ls: true" in combined, combined


def test_schemastore_loads(host):
    """b0o/schemastore.nvim must be installed so jsonls schemas resolve."""
    cmd = host.run(
        "%s --headless "
        "-c \"lua print('schemastore: ' .. tostring(pcall(require, 'schemastore')))\" -c q",
        LVIM,
    )
    combined = cmd.stdout + cmd.stderr
    assert "schemastore: true" in combined, combined


NONE_LS_DIR = "/root/.local/share/lunarvim/site/pack/lazy/opt/none-ls.nvim"

# The revision LunarVim's snapshots/default.json pins. It calls
# `lsp._request_name_to_capability`, which Neovim 0.11 moved to
# `vim.lsp.protocol._request_name_to_capability`, so it throws on every LSP attach.
BROKEN_NONE_LS = "3a4826687da4310af379515086d71faca4d21288"


def _config_lua_none_ls_pin() -> str:
    """The none-ls `commit` pinned by the repo's config.lua."""
    import re
    from pathlib import Path

    text = Path(__file__).resolve().parents[2].joinpath("config.lua").read_text()
    text = re.sub(r"^[ \t]*--.*$", "", text, flags=re.MULTILINE)
    start = text.find('"nvimtools/none-ls.nvim"')
    assert start != -1, "config.lua no longer declares none-ls"
    window = text[start:]
    end = window.find("\n  {", 1)
    if end != -1:
        window = window[:end]
    m = re.search(r'commit\s*=\s*"([0-9a-fA-F]{7,40})"', window)
    assert m, "config.lua must pin none-ls; the snapshot pin crashes on Neovim 0.11"
    return m.group(1)


def test_none_ls_matches_config_pin(host):
    """The image must honor config.lua's none-ls pin, not LunarVim's snapshot pin.

    LunarVim stamps snapshots/default.json onto every core plugin spec, and none-ls is
    one of them. config.lua's `commit` overrides that, but only once an update pass runs
    with config.lua fully loaded -- which is why the Dockerfile does it after MasonInstall.
    """
    cmd = host.run("git -C %s rev-parse HEAD", NONE_LS_DIR)
    assert cmd.rc == 0, f"none-ls checkout missing\n{cmd.stdout}{cmd.stderr}"
    head = cmd.stdout.strip()

    assert head != BROKEN_NONE_LS, (
        "none-ls is on LunarVim's snapshot pin, which crashes on Neovim 0.11. "
        "The Dockerfile's post-MasonInstall update pass did not apply config.lua's pin."
    )
    assert head == _config_lua_none_ls_pin(), (
        f"image has none-ls {head[:7]}, config.lua pins {_config_lua_none_ls_pin()[:7]}"
    )


def test_none_ls_supports_neovim_011_capability_api(host):
    """The checked-out none-ls must use the API fallback chain, on 0.9 as well as 0.11."""
    cmd = host.run("cat %s/lua/null-ls/client.lua", NONE_LS_DIR)
    assert cmd.rc == 0, cmd.stderr
    assert "lsp.protocol._request_name_to_capability" in cmd.stdout, (
        "none-ls does not support Neovim 0.11's capability map location"
    )


def test_null_ls_attaches_without_capability_error(host):
    """The original bug: opening a shell file threw
    `attempt to index field '_request_name_to_capability'`. Assert it is gone on 0.9.5."""
    cmd = host.run(
        "%s --headless /root/.config/lvim/config.lua "
        "-c \"lua vim.wait(2000)\" -c qa 2>&1",
        LVIM,
    )
    combined = cmd.stdout + cmd.stderr
    assert "_request_name_to_capability" not in combined, combined
