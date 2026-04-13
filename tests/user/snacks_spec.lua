-- Snacks opts are defined inline in config.lua inside the lvim.plugins table.
-- This test loads config.lua (which sets lvim.plugins) and finds the snacks entry.

-- Reset lvim.plugins so config.lua can set it
_G.lvim.plugins = nil
_G.lvim.leader = "space"
_G.lvim.log = { level = "warn" }
_G.lvim.format_on_save = { enabled = false, pattern = {} }
_G.lvim.colorscheme = "lunar"
_G.lvim.keys = { normal_mode = {} }
_G.lvim.lsp = { automatic_configuration = { skipped_servers = {} } }
_G.lvim.builtin.alpha = { active = true, mode = "dashboard" }
_G.lvim.builtin.terminal = { active = true }
_G.lvim.builtin.nvimtree = { setup = { view = { side = "left" }, renderer = { icons = { show = { git = true } } } } }
_G.lvim.builtin.indentlines = { active = true }
_G.lvim.builtin.treesitter = { ensure_installed = {}, highlight = { enable = true } }
_G.lvim.builtin.which_key = { active = true, mappings = {} }

-- Stub out modules that config.lua requires at top level
package.preload["lvim.lsp.null-ls.formatters"] = function()
  return { setup = function() end }
end
package.preload["lvim.lsp.null-ls.linters"] = function()
  return { setup = function() end }
end
package.preload["lvim.lsp.null-ls.code_actions"] = function()
  return { setup = function() end }
end
package.preload["lvim.lsp.manager"] = function()
  return { setup = function() end }
end

dofile "config.lua"

-- Find the snacks.nvim entry in lvim.plugins
local snacks_opts
for _, plugin in ipairs(lvim.plugins) do
  if type(plugin) == "table" and plugin[1] == "folke/snacks.nvim" then
    snacks_opts = plugin.opts
    break
  end
end

describe("snacks", function()
  it("is present in lvim.plugins", function()
    assert.is_not_nil(snacks_opts)
  end)

  it("enables safe modules", function()
    assert.is_true(snacks_opts.bigfile.enabled)
    assert.is_false(snacks_opts.notifier.enabled) -- disabled: requires nvim 0.10+
    assert.is_true(snacks_opts.quickfile.enabled)
    assert.is_true(snacks_opts.statuscolumn.enabled)
    assert.is_true(snacks_opts.words.enabled)
    assert.is_true(snacks_opts.scroll.enabled)
  end)

  it("disables modules that conflict with LunarVim built-ins", function()
    assert.is_false(snacks_opts.dashboard.enabled)
    assert.is_false(snacks_opts.terminal.enabled)
    assert.is_false(snacks_opts.indent.enabled)
  end)

  it("disables picker and explorer to avoid replacing telescope and nvimtree", function()
    assert.is_false(snacks_opts.picker.enabled)
    assert.is_false(snacks_opts.explorer.enabled)
  end)
end)
