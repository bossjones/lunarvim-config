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
