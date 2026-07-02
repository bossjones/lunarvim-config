# Spec: Full LunarVim config for Python + DevOps

> **This is the validated implementation spec.** Execute it via `/agent-harness:build`.
> Source plan: `~/.claude/plans/i-want-you-to-silly-gadget.md`.

---

## Context

This repo is a personal LunarVim config (branch `release-1.3/neovim-0.9`) deployed to `~/.config/lvim/`. The **live** entry point is a slim, self-contained `config.lua` ("Python + Shell focused") plus a handful of `ftplugin/*` files. The large `lua/user/*` module tree documented in `CLAUDE.md` is **dormant legacy** — `config.lua` does not `require` it. `CLAUDE.md` is partly stale.

The user wants a config that works well for:
- **Python**: ruff, basedpyright, pytest
- **DevOps files**: `~/.ssh/config`, `.ini`, systemd unit files (`.service`/`.timer`/...), launchd `.plist`, shell scripts, YAML, JSON, XML
- Global tools installed via **uv** (`uv tool install` / `uvx`), never pip/npm-global where a Python tool exists
- **Docker** used to prove the config loads
- **Tests** validating the config via **testinfra** (pytest) run with `uv run pytest`

The config is already ~70% there. This spec closes the specific gaps without disturbing the dormant legacy tree.

## Objective

When complete:
1. Python uses **basedpyright** (LSP, installed via `uv tool install basedpyright`) + **ruff** (format+lint via null-ls) + **pytest** (neotest/dap — already wired).
2. DevOps files highlight and, where a server exists, get LSP: YAML (yamlls), JSON (jsonls, new), TOML (taplo), Dockerfile (dockerls), shell (bashls), XML/`.plist` (treesitter only), `.ini`/systemd/`~/.ssh/config` (treesitter highlighting via parser aliases).
3. `make docker-test` proves the config loads and all servers/tools are present in the container.
4. `uv run pytest` runs a **testinfra** suite asserting the container's binaries, files, filetype detection, and headless config load. Existing plenary Lua tests are kept.

## Design Decisions (confirmed with user)

| Decision | Choice |
|---|---|
| XML / `.plist` support | **Builtin syntax highlighting**, **no lemminx / no Java**. (The nvim-0.9 treesitter pin has no `xml`/`ssh_config` parser, so these use Neovim's builtin `syntax/*.vim` — discovered during the build; outcome is identical for the user: highlighting, no Java.) |
| Python LSP | **Replace pyright fully with basedpyright**, installed via `uv tool install basedpyright` |
| Config validation | **testinfra** (pytest + pytest-testinfra) against the running Docker container; keep plenary Lua tests |
| Blast radius | **Minimal** — touch only `config.lua`, `ftplugin/*`, `Dockerfile`, `Makefile`, `doctor.py`, CI, and new test files. Leave dormant `lua/user/*` alone |
| Global Python tools | via `uv tool install` (basedpyright, ruff). Non-Python LSPs (yamlls/jsonls/taplo/dockerls/bashls) stay on **Mason** |

## Relevant Files

Live files to modify:
- `config.lua` — LSP skip list, treesitter `ensure_installed`, filetype + treesitter-parser aliases, plugin list. Entry point.
- `ftplugin/python.lua` — rewrite pyright → **basedpyright** (with manual-registration fallback).
- `ftplugin/json.lua` — **new**: jsonls setup + SchemaStore.
- `Dockerfile` — MasonInstall list (drop pyright, add json/yaml/taplo/docker servers); `uv tool install basedpyright ruff`; headless treesitter parser install.
- `Makefile` — add `uv tool install basedpyright`; add `test-testinfra` target.
- `script/doctor.py` — required-check list: add basedpyright/jsonls/yamlls/taplo/dockerls, drop pyright.
- `.github/workflows/test.yml` — add a `testinfra` job.
- `lsp-settings/` — add `basedpyright.json`, remove `pyright.json` (cosmetic; nlsp-settings).

### New Files
- `pyproject.toml` — uv project; dev group = `pytest`, `pytest-testinfra`; pytest `testpaths`.
- `tests/testinfra/conftest.py` — build/run the Docker image, expose a `testinfra` host fixture, tear down.
- `tests/testinfra/test_binaries.py` — assert nvim/lvim, uv/uvx, ruff, basedpyright, and Mason LSP binaries exist.
- `tests/testinfra/test_config_load.py` — headless `config loaded ok` + `pcall(require,'snacks')`.
- `tests/testinfra/test_filetypes.py` — filetype detection + treesitter parser `.so` presence for devops files.

> Note: existing `tests/` holds Lua `*_spec.lua`. Plenary's `PlenaryBustedDirectory` only collects `*_spec.lua`, and pytest is pointed at `tests/testinfra/` — the two suites don't collide.

## Implementation Phases

### Phase 1: Language servers & filetypes (Lua config)
Swap pyright→basedpyright, add jsonls, add `xml` parser, wire devops filetypes to parsers.

### Phase 2: Provisioning (uv / Mason / Docker)
Make basedpyright/ruff install via uv; make Docker install every referenced server + parser so the image is a faithful test target.

### Phase 3: Testing (testinfra) & health check
Add the uv project + testinfra suite + Makefile target + CI job; update `doctor.py`.

## Step by Step Tasks
Execute in order, top to bottom.

### 1. Rewrite `ftplugin/python.lua` for basedpyright
- Keep the existing uv `.venv` root-detection logic (`root_files`, `.venv/bin/python`).
- Replace the server name and settings:
  ```lua
  local opts = {
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
      python = { pythonPath = python_path },
    },
  }
  ```
- **Manual-registration fallback** (LunarVim's pinned lspconfig may predate basedpyright):
  ```lua
  local configs = require "lspconfig.configs"
  local lspconfig = require "lspconfig"
  if not lspconfig.basedpyright then
    configs.basedpyright = {
      default_config = {
        cmd = { "basedpyright-langserver", "--stdio" },
        filetypes = { "python" },
        root_dir = get_root_dir,
        settings = { basedpyright = { analysis = { autoSearchPaths = true, useLibraryCodeForTypes = true, diagnosticMode = "openFilesOnly" } } },
      },
    }
  end
  require("lvim.lsp.manager").setup("basedpyright", opts)
  ```

### 2. Update `config.lua`
- **Skip list**: replace `"pyright"` with `"basedpyright"`; add `"jsonls"`:
  ```lua
  vim.list_extend(lvim.lsp.automatic_configuration.skipped_servers, { "basedpyright", "bashls", "jsonls" })
  ```
- **Treesitter**: the nvim-0.9 pin has no `xml`/`ssh_config` parser, so do NOT add them; also drop the pre-existing (never-installable) `ssh_config` entry. The `ini` parser (available) covers `.ini`/systemd/dosini via the aliases below.
- **DevOps filetype + parser aliases** — add near the existing `vim.filetype.add` block:
  ```lua
  vim.filetype.add {
    extension = {
      plist = "xml",
      service = "systemd", timer = "systemd", socket = "systemd",
      mount = "systemd", automount = "systemd", target = "systemd",
      path = "systemd", slice = "systemd", scope = "systemd",
    },
    filename = { ["config"] = function(path) return path:match("%.ssh/config$") and "sshconfig" or nil end },
    pattern = { [".*/%.ssh/config"] = "sshconfig" },
  }
  -- Map devops filetypes to the `ini` parser for highlighting (ini is available;
  -- xml/ssh_config are not on this pin → builtin syntax handles those).
  pcall(vim.treesitter.language.register, "ini", "dosini")
  pcall(vim.treesitter.language.register, "ini", "systemd")
  ```
  (`.plist` and systemd units are already detected by nvim's builtin ftdetect; the explicit block makes behavior deterministic and testable.)
- **Plugins**: add `{ "b0o/schemastore.nvim" }` to `lvim.plugins` (used by jsonls/yamlls).

### 3. Add `ftplugin/json.lua` (new)
```lua
local ok, schemastore = pcall(require, "schemastore")
local opts = {
  settings = {
    json = {
      validate = { enable = true },
      schemas = ok and schemastore.json.schemas() or {},
    },
  },
}
require("lvim.lsp.manager").setup("jsonls", opts)
vim.opt_local.tabstop = 2
vim.opt_local.shiftwidth = 2
vim.opt_local.expandtab = true
```
- Optionally wire `yamlls` to `schemastore.yaml.schemas()` in `ftplugin/yaml.lua` (keep existing k8s mappings). Low priority.

### 4. Update `lsp-settings/`
- Add `lsp-settings/basedpyright.json` mirroring the analysis defaults; delete `lsp-settings/pyright.json`.

### 5. Update `Dockerfile`
- MasonInstall line: drop `pyright`, add the servers the ftplugins actually use:
  ```
  MasonInstall bash-language-server yaml-language-server json-lsp taplo \
    dockerfile-language-server shellcheck shfmt debugpy stylua lua-language-server
  ```
- Add global Python tools via uv (uv/uvx already in the image, `/root/.local/bin` on PATH):
  ```dockerfile
  RUN uv tool install basedpyright && uv tool install ruff
  ```
- **Reliable plugin install** — replace `+"Lazy! sync" +qa` (which does not block until
  headless clones finish, leaving snacks/null-ls/neotest half-installed) with a blocking sync:
  ```dockerfile
  RUN /root/.local/bin/lvim --headless \
    -c "lua require('lazy').sync({ wait = true, show = false })" -c "qa" 2>&1 || true
  ```
- Compile only parsers that exist in the pin (no `xml`/`ssh_config`):
  ```dockerfile
  RUN /root/.local/bin/lvim --headless \
    +"TSInstallSync bash python lua json jsonc yaml toml ini dockerfile" +qa 2>&1 || true
  ```

### 6. Update `Makefile`
- `uv-tool-install`: add `uv tool install basedpyright` (keep `ruff`).
- Add targets:
  ```make
  test-testinfra: docker-build ## Run testinfra suite against the Docker image
  	uv run pytest tests/testinfra -v

  test-all: test test-testinfra ## Run Lua plenary + Python testinfra suites
  ```

### 7. Add uv project + testinfra suite (new files)
- `pyproject.toml`:
  ```toml
  [project]
  name = "lunarvim-config-tests"
  version = "0.0.0"
  requires-python = ">=3.10"

  [dependency-groups]
  dev = ["pytest>=8", "pytest-testinfra>=10"]

  [tool.pytest.ini_options]
  testpaths = ["tests/testinfra"]
  ```
- `tests/testinfra/conftest.py`: session-scoped fixture that runs the prebuilt image detached (`docker run -d --rm lunarvim-config:test sleep infinity`), yields `testinfra.get_host(f"docker://{cid}")`, and stops it in teardown. Assumes `make docker-build`/`docker-build` dependency already built `lunarvim-config:test`.
- `test_binaries.py`: assert present — `nvim`, `~/.local/bin/lvim`, `uv`, `uvx`, `ruff`, `basedpyright` (uv tools bin), and Mason bins for `bash-language-server`, `yaml-language-server`, `taplo`, `dockerfile-language-server`, plus a json-lsp bin (`vscode-json-language-server`). Use `host.exists(...)` / `host.file(path).exists`.
- `test_config_load.py`: run `lvim --headless -c "lua print('config loaded ok')" -c q` → assert `rc == 0` and `config loaded ok` in output; second run asserts `pcall(require,'snacks')` is `true`.
- `test_filetypes.py`: for each of a `.plist`, a `.service`, a `.ssh/config`, a `.ini`, a `.yaml`, a `.json` file, run headless lua to write the file, `:edit` it, and print `&filetype`; assert expected filetype (`xml`, `systemd`, `sshconfig`, `dosini`, `yaml`, `json`). Also assert parser `.so` files exist under the LunarVim treesitter parser dir (at least `xml`, `ssh_config`, `ini`).

### 8. Update `script/doctor.py`
- In the required binaries/Mason/uv-tool check lists: **add** `basedpyright` (uv tool), `yaml-language-server`, `json-lsp`/`vscode-json-language-server`, `taplo`, `dockerfile-language-server`; **remove** `pyright`. Keep `ruff`, `shellcheck`, `shfmt`, `bash-language-server`, `stylua`, `lua-language-server`, `debugpy`.

### 9. Add CI job in `.github/workflows/test.yml`
- New job `testinfra`: checkout → `astral-sh/setup-uv@v4` → `docker build -t lunarvim-config:test .` → `uv run pytest tests/testinfra -v` (timeout ~15 min). Keep existing `install-doctor` and `plenary-tests` jobs.

### 10. Validate end-to-end
- Run the Validation Commands below; all must pass.

## Testing Strategy

- **Unit (Lua)**: existing plenary specs (`make test`) — unchanged; guard against config regressions.
- **Integration (testinfra/Python)**: `uv run pytest tests/testinfra` drives the real Docker image and asserts:
  - toolchain present (nvim/lvim/uv/uvx/ruff/basedpyright + Mason servers),
  - headless config loads cleanly and snacks loads,
  - devops filetypes are detected and their treesitter parsers are compiled.
- **CI**: `ci.yml` (lint + headless + docker-validate) unchanged; `test.yml` gains the `testinfra` job.
- **Edge cases**: basedpyright missing from pinned lspconfig (handled by manual-registration fallback); treesitter parsers not auto-installing headlessly (handled by explicit `TSInstallSync`); tests/ name collision (avoided — pytest `testpaths` + plenary `*_spec.lua` glob are disjoint).

## Acceptance Criteria

- Opening a `.py` file starts **basedpyright** (`:LspInfo`), and `basedpyright` resolves via `uv tool`; ruff still formats/lints on save.
- Opening `.json` starts **jsonls**; `.yaml` starts yamlls; `.toml` taplo; `Dockerfile` dockerls; `.sh` bashls.
- `~/.ssh/config`, `.ini`, systemd units, and `.plist` files are correctly detected and syntax-highlighted (no LSP required).
- `make docker-test` passes.
- `uv run pytest tests/testinfra` passes (all binaries, config load, filetype assertions green).
- `make test` (plenary) still passes.
- `make doctor` passes with basedpyright/jsonls/yamlls/taplo/dockerls present and no pyright requirement.
- No changes to the dormant `lua/user/*` tree.

## Validation Commands

- `docker build -t lunarvim-config:test .` — image builds.
- `make docker-test` — headless config load + snacks check pass.
- `uv run pytest tests/testinfra -v` — testinfra suite green.
- `make test` — plenary Lua specs pass.
- `make doctor` — health check exit 0.
- `luacheck . --globals lvim vim Snacks` and `stylua --check .` — lint/format clean (CI parity).
- Manual smoke: `lvim ~/.ssh/config` then `:echo &filetype` → `sshconfig`; `lvim foo.plist` → `xml`; `lvim foo.service` → `systemd`.

## Notes

- New Python deps via uv only: `uv add --group dev pytest pytest-testinfra` (or the `pyproject.toml` above + `uv sync`).
- `basedpyright` binary is `basedpyright-langserver` for the LSP `cmd`; the CLI is `basedpyright`.
- Docker image is `linux/amd64` (nvim 0.9.5 x86_64 only) — testinfra runs against it via Rosetta on Apple Silicon; the `docker-build` dependency in `test-testinfra` ensures the image exists first.
- `CLAUDE.md` is stale (claims `config.lua` calls `require("user.null_ls")`). Out of scope to fix here, but worth a follow-up note.
- **ruff via native LSP, not null-ls (discovered during build, required fix):** the none-ls fork moved the `ruff` and `shellcheck` builtins out to `none-ls-extras`, so LunarVim's `null-ls.formatters/linters` could not load them. Rather than depend on the extras repo, ruff now runs as its **own LSP server** (`ruff server`, from `uv tool install ruff`) configured in `ftplugin/python.lua` for lint + format + code actions; basedpyright owns types/hover; shellcheck diagnostics come from **bashls** (`shellcheckPath`, already configured). null-ls keeps only shfmt + stylua (still in none-ls core). Two LunarVim-internal gotchas fixed along the way: (a) custom lspconfig servers (basedpyright, ruff) must be registered via `require("lspconfig.configs")` — reading the key off the top-level `lspconfig` raises "Cannot access configuration"; (b) `manager.setup` must be passed an explicit `cmd`, or LunarVim's `launch_server` falls back to the non-existent `lspconfig.server_configurations.<name>` and silently never starts the server. Also: LunarVim bakes per-filetype LSP templates during install (default skip list → includes pyright), so the `Dockerfile` regenerates templates after config sync (`require('lvim.lsp.templates').remove_template_files()/generate_templates()`) so pyright is not auto-installed/attached. Verified: opening a `.py` file attaches exactly `basedpyright` + `ruff`.
- **null-ls → none-ls (discovered during build, required fix):** LunarVim 1.3 pins `jose-elias-alvarez/null-ls.nvim`, whose upstream repo was **deleted**, so its clone fails. That failure cascaded: `config.lua`'s top-level `formatters.setup` (which `require`s null-ls) threw, aborting config load *before* `lvim.plugins`, so **no user plugins installed** (snacks, neotest, dap-python, ...). Fixes applied to `config.lua`: (1) disable the dead core plugin (`{ "jose-elias-alvarez/null-ls.nvim", enabled = false }`) and install the maintained fork (`nvimtools/none-ls.nvim`, which provides the same `null-ls` module); (2) wrap the null-ls formatter/linter/code-action setup in `pcall` so a missing null-ls during first-time bootstrap never aborts config load. The `Dockerfile` also switched to a blocking `require('lazy').sync({ wait = true })` and clears the stale `*.cloning` dir. Verified: 49 plugins install, `require('null-ls')` = true, config loads clean.
