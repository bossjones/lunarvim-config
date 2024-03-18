#!/usr/bin/env bash

# Check if the script is being executed as root
if [ "$(id -u)" = "0" ]; then
    echo "This script should not be run as root."
    exit 1
fi

install_fnm() {
  echo "Installing fnm"
  curl -fsSL https://fnm.vercel.app/install | bash
  # exec "$SHELL" -l
  # fnm
  export PATH="/home/developer/.local/share/fnm:$PATH"
  eval "$(fnm env --use-on-cd)"
  source /home/developer/.zshrc
  fnm install 16.13.1
  fnm use 16.13.1
  npm install -g @fsouza/prettierd
  npm install -g markdownlint-cli
  npm install -g docker-loghose
  npm install -g tree-sitter-cli
}

# SOURCE: https://rtx.pub/install.sh
#region environment setup
get_os() {
  os="$(uname -s)"
  if [ "$os" = Darwin ]; then
    echo "macos"
  elif [ "$os" = Linux ]; then
    echo "linux"
  else
    error "unsupported OS: $os"
  fi
}

# SOURCE: https://rtx.pub/install.sh
get_arch() {
  arch="$(uname -m)"
  if [ "$arch" = x86_64 ]; then
    echo "x64"
  elif [ "$arch" = aarch64 ] || [ "$arch" = arm64 ]; then
    echo "arm64"
  else
    error "unsupported architecture: $arch"
  fi
}

CURRENT_OS="$(get_os)"
# shellcheck disable=SC2034  # Unused variables left for readability
CURRENT_ARCH="$(get_arch)"

get_system() {
  os="$(get_os)"
  arch="$(get_arch)"
}



display_tarball_platform_dash() {
  # https://en.wikipedia.org/wiki/Uname

  local os="unexpected_os"
  local uname_a="$(uname -a)"
  case "${uname_a}" in
  Linux*) os="linux" ;;
  Darwin*) os="darwin" ;;
  SunOS*) os="sunos" ;;
  AIX*) os="aix" ;;
  CYGWIN*) echo_red >&2 "Cygwin is not supported by n" ;;
  MINGW*) echo_red >&2 "Git BASH (MSYS) is not supported by n" ;;
  esac

  local arch="unexpected_arch"
  local uname_m="$(uname -m)"
  case "${uname_m}" in
  x86_64) arch=x64 ;;
  i386 | i686) arch="x86" ;;
  aarch64) arch=arm64 ;;
  armv8l) arch=arm64 ;; # armv8l probably supports arm64, and there is no specific armv8l build so give it a go
  *)
    # e.g. armv6l, armv7l, arm64
    arch="${uname_m}"
    ;;
  esac
  # Override from command line, or version specific adjustment.
  [ -n "$ARCH" ] && arch="$ARCH"

  echo "${os}-${arch}"
}

display_tarball_platform_underscore() {
  # https://en.wikipedia.org/wiki/Uname

  local os="unexpected_os"
  local uname_a="$(uname -a)"
  case "${uname_a}" in
  Linux*) os="linux" ;;
  Darwin*) os="darwin" ;;
  SunOS*) os="sunos" ;;
  AIX*) os="aix" ;;
  CYGWIN*) echo_red >&2 "Cygwin is not supported by n" ;;
  MINGW*) echo_red >&2 "Git BASH (MSYS) is not supported by n" ;;
  esac

  local arch="unexpected_arch"
  local uname_m="$(uname -m)"
  case "${uname_m}" in
  x86_64) arch=x64 ;;
  i386 | i686) arch="x86" ;;
  aarch64) arch=arm64 ;;
  armv8l) arch=arm64 ;; # armv8l probably supports arm64, and there is no specific armv8l build so give it a go
  *)
    # e.g. armv6l, armv7l, arm64
    arch="${uname_m}"
    ;;
  esac
  # Override from command line, or version specific adjustment.
  [ -n "$ARCH" ] && arch="$ARCH"

  echo "${os}_${arch}"
}

###################################################################################################################
# if rustup script has been run and ~/.cargo/env exists
###################################################################################################################
if [ -f ~/.cargo/env ]; then
  # if cargo path is set
  if echo "$PATH" | grep -q ".cargo/bin"; then
      echo "Path exists in PATH variable"
  else
      echo "Path does not exist in PATH variable, exporting it now."

      export PATH="~/.cargo/bin:$PATH"

  fi
fi

mkdir -p ~/.local/src || true
mkdir -p ~/.local/bin || true


fnm=$(command -v fnm 2>/dev/null) || fnm=$(dirname "$0")/fnm
[[ -x "$fnm" ]] || install_fnm


###################################################################################################################
# If this is an arm64 workstation, let's compile neovim from source.
###################################################################################################################
if [ "$(uname -m)" = "aarch64" ]; then
  set +e
  export CURRENT_VERSION_NEOVIM=0.9.1
  asdf uninstall neovim "${CURRENT_VERSION_NEOVIM}" || true
  git clone -b "v${CURRENT_VERSION_NEOVIM}" https://github.com/neovim/neovim ~/.local/src/neovim || true
  cd ~/.local/src/neovim || exit
  rm -rf build || true
  export MANPREFIX=$HOME/.local
  make CMAKE_BUILD_TYPE=RelWithDebInfo CMAKE_INSTALL_PREFIX=~/.local CMAKE_INSTALL_MANDIR="$HOME"/.local
  make install
  asdf global neovim system
  nvim --version
  set -e
else
  echo "not centos or aarch64. skipping"
fi


###################################################################################################################
# Make sure all of our base tools are installed
###################################################################################################################
if [ "$CURRENT_OS" != "macos" ]; then
  # shellcheck disable=SC2002 # Useless cat. Consider 'cmd < file | ..' or 'cmd file | ..' instead
  os_name=$(cat /etc/os-release | grep -oP '^NAME="\K[^"]+')
  # Check if the operating system is Ubuntu
  if [ "${os_name}" = "Ubuntu" ]; then
    echo "The operating system is Ubuntu."
    sudo apt install luarocks neofetch -y
    sudo luarocks install luacheck
    curl -L "https://github.com/hadolint/hadolint/releases/download/v2.12.0/hadolint-$(display_tarball_platform_dash)" >~/.local/bin/hadolint && \
      chmod +x ~/.local/bin/hadolint && \
      pip install vim-vint && \
      pip install yapf flake8 black && \
      cd ~/.local/src && \
      wget "https://github.com/errata-ai/vale/releases/download/v2.26.0/vale_2.26.0_$(display_tarball_platform_underscore).tar.gz" -O vale.tar.gz && \
      tar -xvzf vale.tar.gz -C ~/.local/bin && \
      rm vale.tar.gz
  else
    echo "The operating system is not Ubuntu."
  fi
fi

if [ "$CURRENT_OS" = 'linux' ]; then
  cd ~/.local/src
  git clone --filter=blob:none --sparse https://github.com/ryanoasis/nerd-fonts || true
  cd nerd-fonts
  git sparse-checkout add patched-fonts/FiraCode || true
  ./install.sh FiraCode
  cd -
fi



LV_BRANCH='release-1.3/neovim-0.9' bash <(curl -s https://raw.githubusercontent.com/LunarVim/LunarVim/release-1.3/neovim-0.9/utils/installer/install.sh) --install-dependencies -y

cat << EOF > ~/.config/lvim/config.lua
-- Read the docs: https://www.lunarvim.org/docs/configuration
-- Video Tutorials: https://www.youtube.com/watch?v=sFA9kX-Ud_c&list=PLhoH5vyxr6QqGu0i7tt_XoVK9v-KvZ3m6
-- Forum: https://www.reddit.com/r/lunarvim/
-- Discord: https://discord.com/invite/Xb9B4Ny

-- TODO: Try these configs eventually
-- Defaults from lvim

-- SOURCE: https://github.com/LunarVim/starter.lvim/blob/python-ide/config.lua
-- install plugins
lvim.plugins = {
  "ChristianChiarulli/swenv.nvim",
  "stevearc/dressing.nvim",
  "mfussenegger/nvim-dap-python",
  "nvim-neotest/neotest",
  "nvim-neotest/neotest-python",
}

-- lvim.debug = false
-- vim.lsp.set_log_level "error"
-- lvim.log.level = "warn"

lvim.log.level = "warn"
lvim.format_on_save.enabled = false
lvim.colorscheme = "lunar"
lvim.leader = "space"
lvim.keys.normal_mode["<C-s>"] = ":w<cr>"
lvim.builtin.alpha.active = true
lvim.builtin.alpha.mode = "dashboard"
lvim.builtin.terminal.active = true
lvim.builtin.nvimtree.setup.view.side = "left"
lvim.builtin.nvimtree.setup.renderer.icons.show.git = false

-- automatically install python syntax highlighting
lvim.builtin.treesitter.ensure_installed = {
  "awk",
  "bash",
  "c",
  "cmake",
  "cpp",
  "css",
  "diff",
  "dockerfile",
  "git_config",
  "gitattributes",
  "gitcommit",
  "gitignore",
  "ini",
  "javascript",
  "json",
  "lua",
  "make",
  "passwd",
  "python",
  "rst",
  "ruby",
  "rust",
  "toml",
  "tsx",
  "typescript",
  "yaml",
}

lvim.builtin.treesitter.ignore_install = { "haskell" }
lvim.builtin.treesitter.highlight.enable = true

-- Custom vim options
-- vim.opt.relativenumber=true

-- setup formatting
local formatters = require "lvim.lsp.null-ls.formatters"
formatters.setup { { name = "black" }, }
lvim.format_on_save.enabled = true
lvim.format_on_save.pattern = { "*.py" }

-- setup linting
local linters = require "lvim.lsp.null-ls.linters"
linters.setup { { command = "flake8", filetypes = { "python" } } }

-- setup debug adapter
lvim.builtin.dap.active = true
local mason_path = vim.fn.glob(vim.fn.stdpath "data" .. "/mason/")
pcall(function()
  require("dap-python").setup(mason_path .. "packages/debugpy/venv/bin/python")
end)

-- setup testing
require("neotest").setup({
  adapters = {
    require("neotest-python")({
      -- Extra arguments for nvim-dap configuration
      -- See https://github.com/microsoft/debugpy/wiki/Debug-configuration-settings for values
      dap = {
        justMyCode = false,
        console = "integratedTerminal",
      },
      args = { "--log-level", "DEBUG", "--quiet" },
      runner = "pytest",
    })
  }
})

lvim.builtin.which_key.mappings["dm"] = { "<cmd>lua require('neotest').run.run()<cr>",
  "Test Method" }
lvim.builtin.which_key.mappings["dM"] = { "<cmd>lua require('neotest').run.run({strategy = 'dap'})<cr>",
  "Test Method DAP" }
lvim.builtin.which_key.mappings["df"] = {
  "<cmd>lua require('neotest').run.run({vim.fn.expand('%')})<cr>", "Test Class" }
lvim.builtin.which_key.mappings["dF"] = {
  "<cmd>lua require('neotest').run.run({vim.fn.expand('%'), strategy = 'dap'})<cr>", "Test Class DAP" }
lvim.builtin.which_key.mappings["dS"] = { "<cmd>lua require('neotest').summary.toggle()<cr>", "Test Summary" }


-- binding for switching
lvim.builtin.which_key.mappings["C"] = {
  name = "Python",
  c = { "<cmd>lua require('swenv.api').pick_venv()<cr>", "Choose Env" },
}

-- local formatters = require "lvim.lsp.null-ls.formatters"
-- formatters.setup { { name = "black" }}

-- local linters = require "lvim.lsp.null-ls.linters"
-- linters.setup { { command = "flake8", args = { "--ignore=E203" }, filetypes = { "python" } }}
EOF
