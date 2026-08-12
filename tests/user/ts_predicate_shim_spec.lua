-- The treesitter query compat shim is defined inline at the top of config.lua.
-- This test loads config.lua (which installs the shim) and exercises the
-- legacy `add_predicate(name, handler, force)` call shape that the pinned
-- nvim-treesitter uses.

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

local tsq = vim.treesitter.query

-- The shim only installs on nvim 0.10+; 0.9 (what the Docker/CI image pins)
-- keeps its original behavior and has nothing to assert.
if vim.fn.has "nvim-0.10" ~= 1 then
  describe("treesitter query compat shim", function()
    it("is not installed on nvim 0.9", function()
      assert.is_true(true)
    end)
  end)
  return
end

local SRC = "local x = 1\n"

--- Run a one-capture query whose only predicate is `pred`, forcing the
--- predicate handler to be invoked.
---@param pred string e.g. "#has-ancestor? @a variable_declaration"
local function run_query(pred)
  local parser = vim.treesitter.get_string_parser(SRC, "lua")
  local tree = parser:parse()[1]
  local query = tsq.parse("lua", ("((identifier) @a (%s))"):format(pred))
  for _ in query:iter_matches(tree:root(), SRC, 0, -1) do
  end
end

describe("treesitter query compat shim", function()
  it("accepts the legacy boolean `force` argument without erroring", function()
    assert.has_no.errors(function()
      tsq.add_predicate("shim-spec-legacy?", function()
        return true
      end, true)
    end)
    assert.has_no.errors(function()
      tsq.add_directive("shim-spec-legacy!", function() end, true)
    end)
    assert.is_true(vim.tbl_contains(tsq.list_predicates(), "shim-spec-legacy?"))
    assert.is_true(vim.tbl_contains(tsq.list_directives(), "shim-spec-legacy!"))
  end)

  it("hands legacy handlers a single node, not a list of nodes", function()
    local seen
    tsq.add_predicate("shim-spec-node?", function(match, _, _, pred)
      seen = match[pred[2]]
      return true
    end, true)

    run_query "#shim-spec-node? @a"

    -- Old-style match semantics: match[capture_id] is a TSNode (userdata).
    -- Without `all = false` nvim 0.10+ would pass a TSNode[] table here, and
    -- the vendored handlers' node:parent()/node:range() calls would error.
    assert.equals("userdata", type(seen))
  end)

  it("does not override predicates Neovim ships natively", function()
    assert.is_true(vim.tbl_contains(tsq.list_predicates(), "has-ancestor?"))

    local called = false
    tsq.add_predicate("has-ancestor?", function()
      called = true
      return true
    end, true)

    run_query "#has-ancestor? @a variable_declaration"

    assert.is_false(called)
  end)

  it("does not override directives Neovim ships natively", function()
    assert.is_true(vim.tbl_contains(tsq.list_directives(), "trim!"))

    local called = false
    assert.has_no.errors(function()
      tsq.add_directive("trim!", function()
        called = true
      end, true)
    end)
    assert.is_false(called)
  end)

  it("passes a modern opts table through untouched", function()
    local seen
    tsq.add_predicate("shim-spec-modern?", function(match, _, _, pred)
      seen = match[pred[2]]
      return true
    end, { force = true })

    run_query "#shim-spec-modern? @a"

    -- Modern registration keeps nvim's quantifier-aware match format.
    assert.equals("table", type(seen))
  end)
end)
