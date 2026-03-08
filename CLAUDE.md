# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a LunarVim configuration repository — a highly customized Neovim setup built on top of [LunarVim](https://www.lunarvim.org/) (release-1.3/neovim-0.9 branch). It is a personal config that gets deployed to `~/.config/lvim/`.

## Setup

```bash
# Full bootstrap (installs LunarVim + dependencies)
make bootstrap
# or directly:
./bootstrap.sh

# Sync config files to ~/.config/lvim/
make sync

# Install linters/formatters on macOS (arm64)
make macos-arm64

# Install linters/formatters on Ubuntu (arm64)
make ubuntu

# Install linters/formatters on Ubuntu (x86_64)
make ubuntu-64-bit
```

## Architecture

The entry point is `config.lua` (deployed to `~/.config/lvim/config.lua`). It:
1. Sets global `lvim.*` options that control which features/plugins are active
2. Calls `require("user.null_ls").config()` to configure linters and formatters
3. Skips several LSP servers from auto-configuration (gopls, pyright, rust_analyzer, etc.) in favor of dedicated plugin setups

### `lua/user/` — Core configuration modules

Each file exports a module with a `.config()` method:

- **`null_ls/init.lua`** — Central linter/formatter setup via null-ls. Configures formatters (prettier, prettierd, ruff, black, stylua, gofmt, etc.) and linters (flake8, selene, luacheck, golangci-lint, hadolint, shellcheck, vale, semgrep, etc.)
- **`null_ls/go.lua`** — Custom Go code actions (gostructhelper)
- **`null_ls/markdown.lua`** — Custom markdown hover provider
- **`builtin.lua`** — Overrides LunarVim built-in plugin defaults (cmp, telescope, treesitter, nvimtree, etc.)
- **`plugins.lua`** — Full plugin list for lazy.nvim. Time-based colorscheme switching (rose-pine at night, kanagawa late night, catppuccin evening, lunar daytime)
- **`keybindings.lua`** — Custom key mappings (leader = Space)
- **`autocommands.lua`** — Custom autocommands
- **`lsp_kind.lua`** — Icon/UI configuration for LSP
- **`theme.lua`** — Theme setup functions called from `plugins.lua`
- **`neovim.lua`** — Base Neovim vim options

### Language-specific modules (in `lua/user/`)

`go.lua`, `rust_tools.lua`, `metals.lua`, `flutter_tools.lua`, `tex.lua`, `dap.lua`, `ntest.lua` — each sets up language-specific LSP/tooling when the corresponding `lvim.builtin.*_programming` flag is enabled in `config.lua`.

### Other directories

- **`after/ftplugin/`** — Filetype-specific settings run after plugin load
- **`ftdetect/`** — Custom filetype detection rules
- **`ftplugin/`** — Filetype-specific settings
- **`lsp-settings/`** — Per-language JSON configs for LSP servers
- **`snippets/`** — LuaSnip snippet files
- **`lua/telescope/`** — Telescope extension configurations
- **`lua/lualine/`** — Custom lualine statusline components

## Feature Flags in `config.lua`

Most features are toggled via `lvim.builtin.*` flags. Key ones:

| Flag | Default | Purpose |
|------|---------|---------|
| `fancy_statusline.active` | `true` | Custom lualine |
| `harpoon.active` | `true` | Harpoon file marks |
| `neoclip.active` | `true` | Clipboard manager |
| `tabnine.active` | `true` | TabNine completion |
| `go_programming.active` | `false` | Enable gopher.nvim + dap-go |
| `python_programming.active` | `false` | Enable swenv + dap-python |
| `rust_programming.active` | `false` | Enable rust-tools + crates |
| `dap.active` | `false` | Debug adapter protocol |
| `noice.active` | `false` | Noice UI overrides |
| `tree_provider` | `"nvimtree"` | Can be `"neo-tree"` |
| `motion_provider` | `"hop"` | Can be `"leap"` |
| `task_runner` | `""` | Can be `"async_tasks"` or `"overseer"` |

## Linting/Formatting Tools

The `null_ls/init.lua` dynamically enables tools based on what's installed. Required external tools (installed via `make macos-arm64` or equivalent):

- **Lua**: `luacheck` (luarocks) or `selene` (cargo)
- **Python**: `black`, `flake8`, `ruff`, `yapf`, `isort`, `pylint`
- **Go**: `gofmt`, `golangci-lint`, `revive`, `gostructhelper`
- **Markdown**: `vale`, `markdownlint-cli`
- **Docker**: `hadolint`
- **JS/TS**: `prettierd` or `prettier`
- **Shell**: `shellcheck`
- **Vim**: `vim-vint`

Vale config: copy `vale_config.ini` to `~/.vale.ini` and `~/.config/vale/`.
