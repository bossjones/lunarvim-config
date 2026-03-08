-- LunarVim Configuration: Python + Shell focused
-- =========================================

-- Core settings
-- =========================================
lvim.leader = "space"
lvim.log.level = "warn"
lvim.colorscheme = "lunar"
lvim.format_on_save.enabled = true
lvim.format_on_save.pattern = { "*.py", "*.sh", "*.bash", "*.lua" }
vim.lsp.set_log_level("error")

-- Vim options
-- =========================================
vim.opt.relativenumber = true
vim.opt.wrap = true
vim.opt.confirm = true
vim.opt.clipboard = "unnamedplus"
lvim.keys.normal_mode["<C-s>"] = ":w<cr>"

-- LunarVim builtins
-- =========================================
lvim.builtin.alpha.active = true
lvim.builtin.alpha.mode = "dashboard"
lvim.builtin.terminal.active = true
lvim.builtin.nvimtree.setup.view.side = "left"
lvim.builtin.nvimtree.setup.renderer.icons.show.git = true
lvim.builtin.dap.active = true
lvim.builtin.indentlines.active = true

-- Treesitter
-- =========================================
lvim.builtin.treesitter.ensure_installed = {
  "bash", "python", "lua",
  "json", "jsonc", "yaml", "toml", "ini",
  "dockerfile", "make", "cmake",
  "diff", "gitcommit", "gitignore", "git_config", "gitattributes",
  "markdown", "markdown_inline", "rst",
  "regex", "vim", "vimdoc",
}
lvim.builtin.treesitter.highlight.enable = true

-- LSP
-- =========================================
-- Only skip pyright (manually configured in ftplugin/python.lua)
vim.list_extend(lvim.lsp.automatic_configuration.skipped_servers, { "pyright" })

-- Formatters
-- =========================================
local formatters = require("lvim.lsp.null-ls.formatters")
formatters.setup({
  { name = "ruff" },
  { name = "shfmt", args = { "-i", "2", "-ci" } },
  { name = "stylua" },
})

-- Linters
-- =========================================
local linters = require("lvim.lsp.null-ls.linters")
linters.setup({
  { name = "ruff" },
  { name = "shellcheck" },
})

-- Code actions
-- =========================================
local code_actions = require("lvim.lsp.null-ls.code_actions")
code_actions.setup({
  { name = "shellcheck" },
})

-- Plugins
-- =========================================
lvim.plugins = {
  { "stevearc/dressing.nvim" },
  { "ChristianChiarulli/swenv.nvim" },
  { "mfussenegger/nvim-dap-python" },
  { "nvim-neotest/nvim-nio" },
  { "nvim-neotest/neotest" },
  { "nvim-neotest/neotest-python" },
}

-- DAP setup (debugpy + pytest)
-- =========================================
local mason_path = vim.fn.glob(vim.fn.stdpath("data") .. "/mason/")
pcall(function()
  require("dap-python").setup(mason_path .. "packages/debugpy/venv/bin/python")
  require("dap-python").test_runner = "pytest"
end)

-- Neotest setup
-- =========================================
pcall(function()
  require("neotest").setup({
    adapters = {
      require("neotest-python")({
        dap = { justMyCode = false, console = "integratedTerminal" },
        args = { "--log-level", "DEBUG", "--quiet" },
        runner = "pytest",
      }),
    },
  })
end)

-- Which-key mappings
-- =========================================
-- Testing
lvim.builtin.which_key.mappings["dm"] = { "<cmd>lua require('neotest').run.run()<cr>", "Test Method" }
lvim.builtin.which_key.mappings["dM"] = { "<cmd>lua require('neotest').run.run({strategy = 'dap'})<cr>", "Test Method DAP" }
lvim.builtin.which_key.mappings["df"] = { "<cmd>lua require('neotest').run.run({vim.fn.expand('%')})<cr>", "Test File" }
lvim.builtin.which_key.mappings["dF"] = { "<cmd>lua require('neotest').run.run({vim.fn.expand('%'), strategy = 'dap'})<cr>", "Test File DAP" }
lvim.builtin.which_key.mappings["dS"] = { "<cmd>lua require('neotest').summary.toggle()<cr>", "Test Summary" }

-- Python env switching (swenv)
lvim.builtin.which_key.mappings["C"] = {
  name = "Python",
  c = { "<cmd>lua require('swenv.api').pick_venv()<cr>", "Choose Env" },
}
