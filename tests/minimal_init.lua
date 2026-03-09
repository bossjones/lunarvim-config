-- Plenary test bootstrap for headless Neovim testing
-- Add plenary and repo root to runtimepath
local plenary_path = os.getenv "PLENARY_PATH" or "/tmp/plenary.nvim"
vim.opt.runtimepath:append(plenary_path)
vim.opt.runtimepath:append "."

-- Minimal lvim mock so user modules that reference lvim don't crash on require
_G.lvim = {
  builtin = {
    time_based_themes = true,
    global_statusline = false,
    dap = { active = false },
    noice = { active = false },
    test_runner = { active = false, runner = "neotest" },
    gitsigns = { active = true },
    which_key = { active = true },
    tree_provider = "nvimtree",
    motion_provider = "hop",
    task_runner = "",
    tag_provider = "",
  },
  transparent_window = false,
  colorscheme = "lunar",
}

require "plenary.busted"
