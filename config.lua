-- LunarVim Configuration: Python + Shell focused
-- =========================================

-- Treesitter query compat shim
-- =========================================
-- LunarVim 1.3 pins a 2023-era nvim-treesitter (see lazy-lock.json) that
-- registers all of its predicates/directives with the pre-0.10 signature
-- add_predicate(name, handler, force), where `force` is a BOOLEAN. On nvim 0.10+:
--   * anything wrapping these functions must not assume arg 3 is a table --
--     indexing the boolean `true` crashes nvim-treesitter's module load on
--     every BufReadPre (i.e. opening any file);
--   * a handler registered that way is handed table<capture_id, TSNode[]>
--     instead of table<capture_id, TSNode> unless it opts in with all = false,
--     so the vendored handlers' node:parent()/node:range() calls blow up in
--     queries using #nth? / #has-ancestor? / #is? / #has-type? (go, c, cpp,
--     java, ...);
--   * nvim itself now ships has-ancestor?, has-parent? and trim!, and the
--     vendored copies would override them with older, arg-unaware versions.
-- Normalize the legacy call shape, keep Neovim's own implementations, and give
-- everything else old-style match semantics. Must run before any plugin
-- (including nvim-treesitter, lazy-loaded on BufReadPre) can call these.
if vim.fn.has "nvim-0.10" == 1 then
  local tsq = vim.treesitter.query
  for fn_name, list_name in pairs {
    add_predicate = "list_predicates",
    add_directive = "list_directives",
  } do
    local orig = tsq[fn_name]
    tsq[fn_name] = function(name, handler, opts)
      -- Modern caller (opts table): pass through untouched.
      if type(opts) == "table" then
        return orig(name, handler, opts)
      end
      -- Legacy caller: arg 3 is a boolean `force` (or nil).
      if vim.tbl_contains(tsq[list_name](), name) then
        return -- Neovim (or an earlier registration) already provides this one.
      end
      return orig(name, handler, { force = opts == true, all = false })
    end
  end
end

-- Core settings
-- =========================================
lvim.leader = "space"
lvim.log.level = "warn"
lvim.colorscheme = "lunar"
lvim.format_on_save.enabled = true
lvim.format_on_save.pattern = {
  "*.py",
  "*.sh",
  "*.bash",
  "*.zsh",
  "*.lua",
  -- Languages enabled via LunarVim supported-languages docs. Formatting is
  -- provided by each language's LSP (gopls/clangd/terraformls/jsonls/tsserver/
  -- solargraph). YAML/Ansible are intentionally excluded (no LSP formatter).
  "*.go",
  "*.tf",
  "*.tfvars",
  "*.json",
  "*.jsonc",
  "*.c",
  "*.cc",
  "*.cpp",
  "*.cxx",
  "*.h",
  "*.hpp",
  "*.hh",
  "*.js",
  "*.jsx",
  "*.mjs",
  "*.cjs",
  "*.ts",
  "*.tsx",
  "*.rb",
}
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
  "query",
  -- Languages enabled via LunarVim supported-languages docs
  "go",
  "gomod",
  "gosum",
  "c",
  "cpp",
  "javascript",
  "typescript",
  "tsx",
  "jsdoc",
  "ruby",
  "terraform",
}
lvim.builtin.treesitter.highlight.enable = true

-- LSP
-- =========================================
-- Skip servers we manually configure (or don't want auto-installed):
--   basedpyright + ruff -> ftplugin/python.lua, jsonls -> ftplugin/json.lua, bashls below.
--   pyright is skipped so LunarVim doesn't auto-install it as a python fallback.
vim.list_extend(
  lvim.lsp.automatic_configuration.skipped_servers,
  { "pyright", "basedpyright", "ruff", "bashls", "jsonls" }
)

-- Formatters (null-ls / none-ls)
-- =========================================
-- Only shfmt + stylua go through null-ls: the none-ls fork moved ruff and
-- shellcheck builtins out to none-ls-extras, so we handle those elsewhere —
--   ruff       -> native ruff LSP server (ftplugin/python.lua)
--   shellcheck -> bashls (shellcheckPath, configured below)
-- Guarded with pcall so a missing null-ls during first-time bootstrap does NOT
-- abort config load (which would stop `lvim.plugins` from registering).
pcall(function()
  local formatters = require "lvim.lsp.null-ls.formatters"
  formatters.setup {
    { name = "shfmt", args = { "-i", "2", "-ci" } },
    { name = "stylua" },
  }
end)

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

-- DevOps filetype detection (deterministic + testable). Neovim's builtin ftdetect
-- already handles most of these, but declaring them explicitly makes behavior
-- predictable and lets our tests assert on it.
vim.filetype.add {
  extension = {
    plist = "xml",
    service = "systemd",
    timer = "systemd",
    socket = "systemd",
    mount = "systemd",
    automount = "systemd",
    target = "systemd",
    path = "systemd",
    slice = "systemd",
    scope = "systemd",
  },
  pattern = {
    [".*/%.ssh/config"] = "sshconfig",
    [".*/ssh/ssh_config"] = "sshconfig",
    -- Ansible: map playbooks/roles to `yaml.ansible` so ansiblels attaches.
    -- The yaml treesitter parser still handles highlighting for this filetype.
    [".*/playbooks/.*%.ya?ml"] = "yaml.ansible",
    [".*/roles/.*/tasks/.*%.ya?ml"] = "yaml.ansible",
    [".*/roles/.*/handlers/.*%.ya?ml"] = "yaml.ansible",
    [".*/playbook%.ya?ml"] = "yaml.ansible",
    [".*/site%.ya?ml"] = "yaml.ansible",
  },
}

-- Map devops filetypes to the `ini` treesitter parser for highlighting.
-- The nvim-0.9 / LunarVim-1.3 treesitter pin has NO xml or ssh_config parsers,
-- so XML/.plist and ~/.ssh/config fall back to Neovim's builtin syntax files
-- (syntax/xml.vim, syntax/sshconfig.vim) — highlighting still works, no Java needed.
pcall(vim.treesitter.language.register, "ini", "dosini")
pcall(vim.treesitter.language.register, "ini", "systemd")

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
  -- LunarVim pins `jose-elias-alvarez/null-ls.nvim`, but that repo was deleted
  -- upstream (clone now fails). Disable the dead core spec and install its
  -- maintained drop-in fork instead; none-ls ships the same `null-ls` Lua module,
  -- so ruff/shfmt/stylua/shellcheck keep working via LunarVim's null-ls wrappers.
  { "jose-elias-alvarez/null-ls.nvim", enabled = false },
  {
    -- none-ls is ALSO a LunarVim core plugin (lvim/lua/lvim/plugins.lua), so
    -- lvim/snapshots/default.json stamps `commit = "3a48266"` (2023-11-29) onto it
    -- unless $LVIM_DEV_MODE is set. That revision calls `lsp._request_name_to_capability`,
    -- which Neovim 0.11 moved to `vim.lsp.protocol._request_name_to_capability` — so it
    -- throws on every LSP attach. Every LunarVim branch (1.3, 1.4, master) carries the
    -- same stale pin, so there is no upstream fix to wait for.
    --
    -- This revision uses the
    -- `lsp.protocol._request_name_to_capability or lsp._request_name_to_capability or ...`
    -- fallback chain and guards its other newer APIs (`vim.uv or vim.loop`, `vim.iter`
    -- behind `has("nvim-0.11")`), so it works on both 0.9 and 0.11.
    --
    -- config.lua's specs are merged AFTER lvim/plugins.lua, and lazy's Spec:merge does
    -- `setmetatable(new, { __index = old })` — so this `commit` shadows the snapshot pin.
    -- Bump it deliberately; `make plugins-update` honors it.
    "nvimtools/none-ls.nvim",
    commit = "c4b82bb63b13856ba4d6b971b7aad3bb38fc6fe2",
    lazy = true,
    dependencies = { "nvim-lua/plenary.nvim" },
  },
  { "stevearc/dressing.nvim" },
  { "b0o/schemastore.nvim" }, -- JSON/YAML schemas for jsonls/yamlls
  { "ChristianChiarulli/swenv.nvim" },
  { "mfussenegger/nvim-dap-python" },
  { "nvim-neotest/nvim-nio" },
  { "nvim-neotest/neotest" },
  { "nvim-neotest/neotest-python" },

  -- DX plugins (curated from LunarVim's example-configurations page)
  -- =========================================
  -- Local Neovim is 0.11.x, but the pinned Docker/CI image runs 0.9.5, so every
  -- spec below stays compatible with both. Only `leap` needs a nvim-0.10 guard.
  -- Maintained forks are used where the example page listed archived plugins.

  -- Diagnostics & LSP
  { "folke/trouble.nvim", cmd = "Trouble", opts = {} }, -- diagnostics/quickfix/refs list
  {
    "ray-x/lsp_signature.nvim",
    event = "InsertEnter",
    opts = { hint_enable = false, floating_window = true },
  },
  { "rmagatti/goto-preview", config = true }, -- peek defs/refs in a floating window
  { "hedyhli/outline.nvim", cmd = { "Outline", "OutlineOpen" }, opts = {} }, -- symbol tree panel

  -- Search & refactor
  { "nvim-pack/nvim-spectre", dependencies = { "nvim-lua/plenary.nvim" } }, -- project search/replace
  { "kevinhwang91/nvim-bqf", ft = "qf" }, -- better quickfix window
  {
    "folke/todo-comments.nvim",
    event = "BufReadPost",
    dependencies = { "nvim-lua/plenary.nvim" },
    config = true,
  },

  -- Git workflow
  {
    "sindrets/diffview.nvim",
    cmd = { "DiffviewOpen", "DiffviewFileHistory" },
    dependencies = { "nvim-lua/plenary.nvim" },
  },
  -- Maintained fork of ruifm/gitlinker (which is unmaintained).
  { "linrongbin16/gitlinker.nvim", cmd = "GitLink", config = true },
  {
    "pwntester/octo.nvim", -- GitHub issues/PRs in-editor (needs `gh`)
    cmd = "Octo",
    dependencies = {
      "nvim-lua/plenary.nvim",
      "nvim-telescope/telescope.nvim",
      "nvim-tree/nvim-web-devicons",
    },
    config = true,
  },

  -- Editing & motion
  { "kylechui/nvim-surround", event = "BufReadPost", config = true }, -- modern vim-surround
  {
    -- leap moved off GitHub to Codeberg; requires Neovim 0.10+, so it is
    -- guarded off on the 0.9.5 CI image.
    url = "https://codeberg.org/andyg/leap.nvim",
    event = "BufReadPost",
    cond = function()
      return vim.fn.has "nvim-0.10" == 1
    end,
    dependencies = { "tpope/vim-repeat" },
    config = function()
      -- Sneak-style mappings. `create_default_mappings()` is deprecated and its
      -- default `S` collides with nvim-surround's visual-mode `S`, so map `S`
      -- only in normal + operator-pending and leave visual `S` to surround.
      vim.keymap.set({ "n", "x", "o" }, "s", "<Plug>(leap-forward)")
      vim.keymap.set({ "n", "o" }, "S", "<Plug>(leap-backward)")
      vim.keymap.set("n", "gs", "<Plug>(leap-from-window)")
    end,
  },
  {
    "nvim-treesitter/nvim-treesitter-context", -- sticky function/class header
    event = "BufReadPost",
    config = function()
      require("treesitter-context").setup { max_lines = 3 }
    end,
  },
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

-- Diagnostics / Trouble / TODOs (<leader>x)
lvim.builtin.which_key.mappings["x"] = {
  name = "Trouble/Diagnostics",
  x = { "<cmd>Trouble diagnostics toggle<cr>", "Workspace Diagnostics" },
  d = { "<cmd>Trouble diagnostics toggle filter.buf=0<cr>", "Document Diagnostics" },
  q = { "<cmd>Trouble qflist toggle<cr>", "Quickfix List" },
  l = { "<cmd>Trouble loclist toggle<cr>", "Location List" },
  r = { "<cmd>Trouble lsp toggle focus=false win.position=right<cr>", "LSP Refs/Defs" },
  s = { "<cmd>Trouble symbols toggle focus=false<cr>", "Symbols" },
  t = { "<cmd>TodoTelescope<cr>", "Search TODOs" },
}

-- Search & replace (Spectre) (<leader>S)
lvim.builtin.which_key.mappings["S"] = {
  name = "Search/Replace",
  s = { "<cmd>lua require('spectre').toggle()<cr>", "Spectre (toggle)" },
  w = { "<cmd>lua require('spectre').open_visual({ select_word = true })<cr>", "Search current word" },
  f = { "<cmd>lua require('spectre').open_file_search({ select_word = true })<cr>", "Search in current file" },
}

-- Symbols outline (<leader>o)
lvim.builtin.which_key.mappings["o"] = { "<cmd>Outline<cr>", "Symbols Outline" }

-- Extra git tools: diffview + gitlinker + octo (<leader>G, to avoid clobbering
-- LunarVim's core `g` gitsigns group)
lvim.builtin.which_key.mappings["G"] = {
  name = "Git+",
  d = { "<cmd>DiffviewOpen<cr>", "Diffview" },
  h = { "<cmd>DiffviewFileHistory<cr>", "History (repo)" },
  H = { "<cmd>DiffviewFileHistory %<cr>", "History (current file)" },
  y = { "<cmd>GitLink<cr>", "Yank git permalink" },
  Y = { "<cmd>GitLink!<cr>", "Open git permalink in browser" },
  o = { "<cmd>Octo pr list<cr>", "Octo: list PRs" },
  i = { "<cmd>Octo issue list<cr>", "Octo: list issues" },
  r = { "<cmd>Octo review start<cr>", "Octo: start review" },
}

-- goto-preview (peek in floating window) and TODO navigation
lvim.keys.normal_mode["gpd"] = "<cmd>lua require('goto-preview').goto_preview_definition()<cr>"
lvim.keys.normal_mode["gpr"] = "<cmd>lua require('goto-preview').goto_preview_references()<cr>"
lvim.keys.normal_mode["gpi"] = "<cmd>lua require('goto-preview').goto_preview_implementation()<cr>"
lvim.keys.normal_mode["gP"] = "<cmd>lua require('goto-preview').close_all_win()<cr>"
lvim.keys.normal_mode["]t"] = "<cmd>lua require('todo-comments').jump_next()<cr>"
lvim.keys.normal_mode["[t"] = "<cmd>lua require('todo-comments').jump_prev()<cr>"
