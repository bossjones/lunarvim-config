local util = require "lspconfig.util"

local root_files = {
  "pyproject.toml",
  "setup.py",
  "setup.cfg",
  "requirements.txt",
  "Pipfile",
  "manage.py",
  "pyrightconfig.json",
  ".python-version",
  "uv.lock",
}

local function get_root_dir(fname)
  return util.root_pattern(unpack(root_files))(fname) or util.root_pattern ".git"(fname) or util.path.dirname(fname)
end

-- Detect uv's .venv in project root
local root_dir = get_root_dir(vim.fn.expand "%:p")
local python_path = nil
if root_dir then
  local venv = root_dir .. "/.venv"
  if vim.fn.isdirectory(venv) == 1 then
    python_path = venv .. "/bin/python"
  end
end

-- LunarVim 1.3 pins an old nvim-lspconfig that predates both basedpyright and
-- ruff's native server, so register them as custom lspconfig servers. The guard
-- MUST check `lspconfig.configs` (the registry) — reading an unknown key off the
-- top-level `lspconfig` module raises "Cannot access configuration for ...".
local configs = require "lspconfig.configs"

if not configs.basedpyright then
  configs.basedpyright = {
    default_config = {
      cmd = { "basedpyright-langserver", "--stdio" },
      filetypes = { "python" },
      root_dir = get_root_dir,
      single_file_support = true,
      settings = {
        basedpyright = {
          analysis = {
            autoSearchPaths = true,
            useLibraryCodeForTypes = true,
            diagnosticMode = "openFilesOnly",
          },
        },
      },
    },
  }
end

if not configs.ruff then
  configs.ruff = {
    default_config = {
      cmd = { "ruff", "server" },
      filetypes = { "python" },
      root_dir = get_root_dir,
      single_file_support = true,
    },
  }
end

-- basedpyright: types, hover, go-to-definition, completion.
-- NOTE: `cmd` MUST be passed explicitly. LunarVim's launch_server falls back to
-- `require("lspconfig.server_configurations.<name>")` when cmd is absent, which
-- does not exist for custom-registered servers and silently aborts the launch.
require("lvim.lsp.manager").setup("basedpyright", {
  cmd = { "basedpyright-langserver", "--stdio" },
  root_dir = get_root_dir,
  single_file_support = true,
  settings = {
    basedpyright = {
      analysis = {
        typeCheckingMode = "standard", -- basedpyright default "recommended" is noisy
        autoSearchPaths = true,
        diagnosticMode = "openFilesOnly",
        useLibraryCodeForTypes = true,
      },
    },
    python = {
      pythonPath = python_path,
    },
  },
})

-- ruff: linting, formatting, code actions via its native LSP server
-- (`ruff server`, installed with `uv tool install ruff`). basedpyright owns hover.
require("lvim.lsp.manager").setup("ruff", {
  cmd = { "ruff", "server" },
  root_dir = get_root_dir,
  single_file_support = true,
  on_attach = function(client, _)
    client.server_capabilities.hoverProvider = false
  end,
})
