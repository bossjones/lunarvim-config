"""Assert the Python LSP setup: basedpyright (types) + ruff (lint/format) attach,
and the old pyright fallback does NOT."""

from __future__ import annotations

import re

PROBE = r"""
vim.fn.writefile({'import os', 'x =1'}, '/root/probe_lsp.py')
vim.cmd('edit /root/probe_lsp.py')
vim.wait(25000, function() return #vim.lsp.get_active_clients() >= 2 end, 250)
local t = {}
for _, c in ipairs(vim.lsp.get_active_clients()) do t[#t + 1] = c.name end
table.sort(t)
io.write('<<CLIENTS=' .. table.concat(t, ',') .. '>>')
"""


def test_python_lsp_clients(run_lua):
    result = run_lua(PROBE)
    combined = result.stdout + result.stderr
    m = re.search(r"<<CLIENTS=(.*?)>>", combined)
    assert m, f"no CLIENTS marker in output\n{combined}"
    clients = [c for c in m.group(1).split(",") if c]

    assert "basedpyright" in clients, f"basedpyright did not attach; clients={clients}"
    assert "ruff" in clients, f"ruff did not attach; clients={clients}"
    # pyright must NOT attach (note: 'basedpyright' contains 'pyright', so match exactly)
    assert "pyright" not in clients, f"stale pyright attached; clients={clients}"
