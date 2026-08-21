# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a LunarVim configuration repository — a customized Neovim setup built on
top of [LunarVim](https://www.lunarvim.org/) (`release-1.3/neovim-0.9` branch). It
is a personal config that gets deployed to `~/.config/lvim/`.

> **Neovim version duality (important):** the LunarVim branch pins **Neovim 0.9**,
> and the Docker/CI image (`make docker-build`) runs **0.9.5** — but a developer's
> local machine may run a much newer Neovim (e.g. 0.11.x). The config must work on
> **both**. That's why you'll see version guards (e.g. `snacks.notifier` disabled,
> `leap` gated behind `nvim-0.10`) and the treesitter-predicate compat shim at the
> top of `config.lua`. Don't introduce 0.10+-only APIs without a guard.

## ⚠️ Architecture — read this first

**`config.lua` is the one and only active entry point** (deployed to
`~/.config/lvim/config.lua`). It is **lean and self-contained**: it sets
`lvim.*` options, treesitter parsers, LSP `skipped_servers`, formatters, a manual
`bashls` setup, filetype detection, Python DAP/neotest, an inline `lvim.plugins`
list, and which-key mappings — all directly, in one file.

**`lua/user/` is DORMANT.** It is a large vendored, Abzcoding-style LunarVim
superset (`plugins.lua`, `builtin.lua`, `keybindings.lua`, `null_ls/`, per-language
modules, etc.). **Nothing in `config.lua` `require`s it.** It is **reference /
precedent only** — mine it for config snippets, but changing it has **no effect**
on the running editor. In particular, the `lvim.builtin.*_programming` flags and
the `tabnine`/`harpoon`/`neoclip` toggles live only in that dormant tree and are
**not** part of the active config.

`config-simple.lua` is a third, even smaller variant that is also not loaded by default.

> If a change is meant to affect the editor, it almost always belongs in
> `config.lua`, `ftplugin/`, or `lsp-settings/` — not `lua/user/`.

## Setup / deploy

```bash
# Full bootstrap (installs LunarVim + dependencies)
make bootstrap            # or ./bootstrap.sh

# Deploy config to ~/.config/lvim/  (PREFERRED: zip-backup + clean install)
make deploy               # preview first with: make deploy ARGS=--dry-run
                          #  ( uv run script/install.py — see specs/install.md )

# Older overlay-copy deploy (kept for compatibility; leaves stale files behind)
make sync

# Install formatters/linters + language toolchains
make macos-arm64          # macOS (Apple Silicon) — non-interactive
make ubuntu               # Ubuntu arm64
make ubuntu-64-bit        # Ubuntu x86_64

# Install LSP servers into Mason (headless)
make mason-tool-install

# Health check
make doctor               # uv run script/doctor.py
```

## What `config.lua` actually contains

- **Core options**: leader = Space, `colorscheme = "lunar"`, `format_on_save`
  enabled with an explicit `pattern` list, relativenumber, wrap, clipboard,
  `<C-s>` = save.
- **Builtins toggled**: `alpha` dashboard, `terminal`, `nvimtree` (left + git
  icons), `dap.active`, `indentlines.active`.
- **Treesitter**: `lvim.builtin.treesitter.ensure_installed` — the canonical list
  of parsers (Python/Shell/Lua/JSON/YAML/DevOps + Go/C/C++/JS/TS/Ruby/Terraform).
- **LSP**: skips `pyright, basedpyright, ruff, bashls, jsonls` (hand-configured
  elsewhere); all other servers are auto-configured by LunarVim from Mason, with
  overrides read from `lsp-settings/*.json`.
- **Formatters**: only `shfmt` + `stylua` go through LunarVim's null-ls wrapper
  (`require("lvim.lsp.null-ls.formatters").setup`). Everything else formats via its
  LSP server.
- **Plugins**: an inline `lvim.plugins` list — `snacks.nvim` (partial), `none-ls`
  (maintained null-ls fork), `dressing`, `schemastore`, `swenv`, Python DAP +
  `neotest`, plus a curated DX set (trouble, lsp_signature, goto-preview, outline,
  spectre, bqf, todo-comments, diffview, gitlinker, octo, nvim-surround, leap,
  treesitter-context).
- **which-key groups**: `d` testing (neotest), `C` Python (swenv), `x`
  diagnostics/Trouble, `S` spectre, `o` outline, `G` git+ (diffview/gitlinker/octo).

## Adding / enabling a language (the established pattern)

1. **Treesitter** — add the parser to `ensure_installed` in `config.lua`.
2. **LSP server** — add it to the `MasonInstall` list in the `mason-tool-install`
   Makefile target. LunarVim auto-configures Mason-installed servers on the matching
   filetype (unless listed in `skipped_servers`). Put per-server settings in
   `lsp-settings/<server>.json` (flat dotted keys, e.g. `gopls.json`).
   - Servers needing custom root detection / registration are hand-set-up in
     `ftplugin/<ft>.lua` via `require("lvim.lsp.manager").setup(...)`. See
     `ftplugin/python.lua` (basedpyright + ruff — note: custom servers **must**
     pass `cmd` explicitly), `json.lua`, `yaml.lua`, `toml.lua`, `dockerfile.lua`.
3. **format-on-save** — add the file glob to `lvim.format_on_save.pattern`. At
   LSP-only depth, formatting comes from the LSP (gopls/clangd/terraformls/jsonls/
   tsserver/solargraph). YAML/Ansible have no LSP formatter — don't add them.
4. **Filetype detection** — extend the `vim.filetype.add` block in `config.lua`
   (e.g. Ansible playbooks/roles → `yaml.ansible` so `ansiblels` attaches).
5. **Tooling** — add binaries to the appropriate Makefile installer target
   (`uv-/npm-/brew-/go-/luarocks-/gem-tool-install` and `macos-arm64`).

`specs/ai-completion.md` documents a planned, opt-in TabNine rollout (not active).

## Directories

- **`ftplugin/`** — per-filetype settings + hand-configured LSP servers.
- **`ftdetect/`** — extra filetype detection (most detection is inline in `config.lua`).
- **`lsp-settings/`** — per-server JSON overrides (auto-loaded by nlsp-settings).
- **`snippets/`** — LuaSnip snippets.
- **`script/`** — `install.py` (the `make deploy` engine) and `doctor.py`.
- **`specs/`** — design/spec docs (installer, ai-completion, etc.).
- **`tests/`** — plenary Lua specs (`tests/user/`) + Python (`tests/unit`, `tests/testinfra`).
- **`lua/user/`** — **DORMANT** vendored superset (precedent only; see Architecture).

## Testing

```bash
make test            # plenary Lua specs (headless; needs plenary at $PLENARY_PATH or /tmp/plenary.nvim)
make test-unit       # fast Python unit tests (pytest)
make test-testinfra  # testinfra suite against the Docker image
make docker-lint     # luacheck inside Docker (use this if local luacheck is broken)
make smoke           # active-system post-deploy smoke suite; missing local tools are reported as skips
make deploy-smoke    # deploy then run the active-system smoke suite
make e2e             # strict Docker smoke suite for Neovim 0.9.5; intentionally nonzero at baseline
```

### Smoke feedback loop

After changes to `config.lua`, `ftplugin/`, `ftdetect/`, `after/`, or
`lsp-settings/`, run `make deploy-smoke` so the active LunarVim runtime exercises
the deployed configuration. Add each regression as a fixture or manifest assertion
first and run it red before making the production change; the fixture turns green only
when the real runtime behavior is fixed.

The headless runner sets `lines` and `columns` to provide stable window geometry.
It writes its machine-readable report to a file for `script/smoke.py` to read, rather
than emitting JSON with `io.write`, because headless runtime output can mix with stdout.

### Strict e2e baseline

The current strict Docker result is intentionally nonzero and the active config must
remain unchanged in this baseline-only work. The authoritative fixture/check evidence,
rationale, and green gate are in
[`specs/smoke-test.md`](specs/smoke-test.md#intentional-red-baseline-and-ci-policy);
it covers shell formatting, Ansible LSP, log/text syntax, Lua runtime/formatting, and
the legitimate `just/*` version skips. Keep every failure visible in the runner report:
do not invert assertions, accept a runner crash, or add `e2e` to `test-all` or CI.

The separate green follow-up resolves every in-range failure from that policy, rechecks
the legitimate version skips, and proves a zero-exit `make e2e` before adding the
blocking `test-all` and CI wiring. It must not use `continue-on-error`.

## Gotchas learned the hard way

- **Don't trust `lua/user/` as active code** — see Architecture. Verify a symbol is
  actually reachable from `config.lua` before assuming a change takes effect.
- **`leap.nvim` moved to Codeberg** (`url = "https://codeberg.org/andyg/leap.nvim"`)
  and requires nvim 0.10+, so its spec is `cond`-guarded; it uses Sneak-style
  mappings so visual-mode `S` stays with `nvim-surround`.
- **`make deploy` may report "0 changes"** if an auto-sync already mirrored the repo
  into `~/.config/lvim/`; the deployed dir, not a symlink, can already be identical.
- **Mason/data dir**: the live LunarVim data dir is `~/.local/share/lvim/`
  (`~/.local/share/lunarvim/` may exist but be stale). Servers install under
  `~/.local/share/lvim/mason/packages/`.
- **Local `luacheck` can be broken** (luarocks Lua-version loader errors); use
  `make docker-lint` for a reliable lint. For quick Lua checks:
  `luajit -bl <file> /dev/null` (parse) and `stylua --check <file>`.

## Linting/Formatting tool inventory

Installed via `make macos-arm64` / `make ubuntu*` / the `*-tool-install` targets:

- **Lua**: `luacheck` (luarocks) or `selene` (cargo, opt-in) · formatter `stylua`
- **Python**: `basedpyright`+`ruff` (LSP), `black`, `flake8`, `isort`, `pylint`, `yapf`
- **Go**: `gopls`, `golangci-lint`, `revive`, `goimports`
- **C/C++**: `clangd` (+ built-in clang-format), `cppcheck`
- **Terraform**: `terraform-ls`, `terraform`, `tflint`
- **JS/TS**: `typescript-language-server`, `prettierd`, `eslint_d`
- **Ruby**: `solargraph`, `rubocop`
- **Ansible/YAML**: `ansible-language-server`, `ansible-lint`, `yamllint`
- **Markdown**: `vale`, `markdownlint-cli` · **Docker**: `hadolint` · **Shell**: `shellcheck`, `shfmt` · **Vim**: `vim-vint`

Vale config: copy `vale_config.ini` to `~/.vale.ini` and `~/.config/vale/`.
