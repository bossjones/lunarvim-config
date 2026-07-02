"""Assert devops filetypes are detected and their treesitter parsers exist.

Uses the `run_lua` fixture (see conftest) which executes Lua *after* config.lua
has been sourced, so our `vim.filetype.add` rules and parser aliases are active.
"""

from __future__ import annotations

import re

import pytest

# (path to create/edit, expected &filetype)
FILETYPE_CASES = [
    ("/root/probe/foo.plist", "xml"),
    ("/root/probe/foo.service", "systemd"),
    ("/root/probe/foo.timer", "systemd"),
    ("/root/.ssh/config", "sshconfig"),
    ("/root/probe/foo.ini", "dosini"),
    ("/root/probe/foo.yaml", "yaml"),
    ("/root/probe/foo.json", "json"),
]

# Treesitter parsers that must be compiled. xml and ssh_config are intentionally
# absent: they don't exist in the nvim-0.9 treesitter pin, so XML/.plist and
# ~/.ssh/config rely on Neovim's builtin syntax highlighting instead (asserted
# separately in test_builtin_syntax_available).
PARSERS = ["ini", "yaml", "json", "bash", "python"]

# Filetypes whose highlighting comes from Neovim's builtin syntax files rather
# than treesitter (no parser available on the pin). We assert the runtime ships
# the syntax file so highlighting is guaranteed.
BUILTIN_SYNTAX = ["xml", "sshconfig"]


def _extract(output: str, token: str) -> str | None:
    m = re.search(rf"<<{token}=(.*?)>>", output)
    return m.group(1) if m else None


@pytest.mark.parametrize("path,expected_ft", FILETYPE_CASES)
def test_filetype_detection(host, run_lua, path, expected_ft):
    host.run("mkdir -p %s", path.rsplit("/", 1)[0])
    host.run("touch %s", path)
    lua = f"""
      vim.cmd('edit {path}')
      io.write('<<FT=' .. vim.bo.filetype .. '>>')
    """
    result = run_lua(lua)
    combined = result.stdout + result.stderr
    got = _extract(combined, "FT")
    assert got == expected_ft, (
        f"{path}: expected filetype '{expected_ft}', got '{got}'\n{combined}"
    )


@pytest.mark.parametrize("parser", PARSERS)
def test_treesitter_parser_installed(host, run_lua, parser):
    lua = f"""
      local ok, parsers = pcall(require, 'nvim-treesitter.parsers')
      local has = ok and parsers.has_parser('{parser}')
      io.write('<<HAS=' .. tostring(has) .. '>>')
    """
    result = run_lua(lua)
    combined = result.stdout + result.stderr
    got = _extract(combined, "HAS")
    assert got == "true", (
        f"treesitter parser '{parser}' not installed (has_parser={got})\n{combined}"
    )


@pytest.mark.parametrize("syntax", BUILTIN_SYNTAX)
def test_builtin_syntax_available(host, run_lua, syntax):
    """XML/.plist and ~/.ssh/config highlight via Neovim's builtin syntax files."""
    lua = f"""
      local files = vim.api.nvim_get_runtime_file('syntax/{syntax}.vim', false)
      io.write('<<SYN=' .. tostring(#files > 0) .. '>>')
    """
    result = run_lua(lua)
    combined = result.stdout + result.stderr
    got = _extract(combined, "SYN")
    assert got == "true", (
        f"builtin syntax file 'syntax/{syntax}.vim' not found in runtime\n{combined}"
    )
