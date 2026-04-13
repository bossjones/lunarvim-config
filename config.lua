-- LunarVim Configuration: Python + Shell focused
-- =========================================

-- Core settings
-- =========================================
lvim.leader = "space"
lvim.log.level = "warn"
lvim.colorscheme = "lunar"
lvim.format_on_save.enabled = true
lvim.format_on_save.pattern = { "*.py", "*.sh", "*.bash", "*.zsh", "*.lua" }
vim.lsp.set_log_level "error"

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
  "bash",
  "python",
  "lua",
  "json",
  "jsonc",
  "yaml",
  "toml",
  "ini",
  "dockerfile",
  "make",
  "cmake",
  "diff",
  "gitcommit",
  "gitignore",
  "git_config",
  "gitattributes",
  "markdown",
  "markdown_inline",
  "rst",
  "regex",
  "vim",
  "vimdoc",
  "json5",
  "hcl",
  "html",
  "css",
  "sql",
  "ssh_config",
  "query",
}
lvim.builtin.treesitter.highlight.enable = true

-- LSP
-- =========================================
-- Skip servers we manually configure (pyright in ftplugin/python.lua, bashls below)
vim.list_extend(lvim.lsp.automatic_configuration.skipped_servers, { "pyright", "bashls" })

-- Formatters
-- =========================================
local formatters = require "lvim.lsp.null-ls.formatters"
formatters.setup {
  { name = "ruff" },
  { name = "shfmt", args = { "-i", "2", "-ci" } },
  { name = "stylua" },
}

-- Linters
-- =========================================
local linters = require "lvim.lsp.null-ls.linters"
linters.setup {
  { name = "ruff" },
  { name = "shellcheck" },
}

-- Code actions
-- =========================================
local code_actions = require "lvim.lsp.null-ls.code_actions"
code_actions.setup {
  { name = "shellcheck" },
}

-- Bash LSP (hover, go-to-definition, completions for shell scripts)
-- =========================================
require("lvim.lsp.manager").setup("bashls", {
  filetypes = { "sh", "bash", "zsh" },
  settings = {
    bashIde = {
      globPattern = "**/*@(.sh|.inc|.bash|.command|.zsh|zshrc|zsh_*)",
      shellcheckPath = "shellcheck",
    },
  },
})

vim.filetype.add {
  extension = { zsh = "zsh" },
  filename = {
    [".zshrc"] = "zsh",
    [".zshenv"] = "zsh",
    [".zprofile"] = "zsh",
  },
}

-- Plugins
-- =========================================
lvim.plugins = {
  {
    "folke/snacks.nvim",
    priority = 1000,
    lazy = false,
    opts = {
      -- Phase 1: non-conflicting modules
      bigfile = { enabled = true },
      notifier = { enabled = false }, -- requires nvim 0.10+; Dockerfile pins 0.9.5
      quickfile = { enabled = true },
      statuscolumn = { enabled = true },
      words = { enabled = true },
      scroll = { enabled = true },
      -- Phase 2: replace LunarVim built-ins (disabled for now)
      dashboard = { enabled = false },
      terminal = { enabled = false },
      indent = { enabled = false },
      dim = { enabled = false },
      picker = { enabled = false },
      explorer = { enabled = false },
    },
  },
  { "stevearc/dressing.nvim" },
  { "ChristianChiarulli/swenv.nvim" },
  { "mfussenegger/nvim-dap-python" },
  { "nvim-neotest/nvim-nio" },
  { "nvim-neotest/neotest" },
  { "nvim-neotest/neotest-python" },
}

-- DAP setup (debugpy + pytest)
-- =========================================
local mason_path = vim.fn.glob(vim.fn.stdpath "data" .. "/mason/")
local debugpy_python = mason_path .. "packages/debugpy/venv/bin/python"
if vim.fn.executable(debugpy_python) ~= 1 then
  local venv_python = vim.fn.getcwd() .. "/.venv/bin/python"
  if vim.fn.executable(venv_python) == 1 then
    debugpy_python = venv_python
  end
end
pcall(function()
  require("dap-python").setup(debugpy_python)
  require("dap-python").test_runner = "pytest"
end)

-- Neotest setup
-- =========================================
pcall(function()
  require("neotest").setup {
    adapters = {
      require "neotest-python" {
        dap = { justMyCode = false, console = "integratedTerminal" },
        args = { "--log-level", "DEBUG", "--quiet" },
        runner = "pytest",
      },
    },
  }
end)

-- Which-key mappings
-- =========================================
-- Testing
lvim.builtin.which_key.mappings["dm"] = { "<cmd>lua require('neotest').run.run()<cr>", "Test Method" }
lvim.builtin.which_key.mappings["dM"] =
  { "<cmd>lua require('neotest').run.run({strategy = 'dap'})<cr>", "Test Method DAP" }
lvim.builtin.which_key.mappings["df"] = { "<cmd>lua require('neotest').run.run({vim.fn.expand('%')})<cr>", "Test File" }
lvim.builtin.which_key.mappings["dF"] =
  { "<cmd>lua require('neotest').run.run({vim.fn.expand('%'), strategy = 'dap'})<cr>", "Test File DAP" }
lvim.builtin.which_key.mappings["dS"] = { "<cmd>lua require('neotest').summary.toggle()<cr>", "Test Summary" }
lvim.builtin.which_key.mappings["do"] = { "<cmd>lua require('neotest').output_panel.toggle()<cr>", "Test Output" }
lvim.builtin.which_key.mappings["dx"] = { "<cmd>lua require('neotest').run.stop()<cr>", "Test Stop" }

-- Python env switching (swenv)
lvim.builtin.which_key.mappings["C"] = {
  name = "Python",
  c = { "<cmd>lua require('swenv.api').pick_venv()<cr>", "Choose Env" },
}

