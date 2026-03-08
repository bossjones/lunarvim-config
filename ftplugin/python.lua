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

local opts = {
  root_dir = get_root_dir,
  settings = {
    pyright = {
      disableLanguageServices = false,
      disableOrganizeImports = false,
    },
    python = {
      analysis = {
        autoSearchPaths = true,
        diagnosticMode = "workspace",
        useLibraryCodeForTypes = true,
        typeCheckingMode = "basic",
      },
      pythonPath = python_path,
    },
  },
  single_file_support = true,
}

require("lvim.lsp.manager").setup("pyright", opts)
