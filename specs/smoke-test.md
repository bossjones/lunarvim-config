# Plan: Two-tier file-opening tests — Docker e2e + active-system smoke

## Task Description

Every time the LunarVim config seems "done", opening some ordinary file (a shell
script, a YAML file, a `.log`, an `ssh_config`, …) surfaces a new runtime error —
a plugin/Neovim-version incompatibility, a missing filetype rule, an LSP that
silently doesn't attach, a treesitter parser that isn't there. The existing tests
don't catch these because:

- `make test` (plenary) runs against a **mocked** `lvim` global, not the real runtime.
- `make test-testinfra` only runs inside the **0.9.5 Docker image** and only checks
  `&filetype` + parser presence for 7 synthetic files — it never opens a real
  buffer end-to-end, and it never exercises the **local** machine (nvim 0.11.x),
  which is where the pain actually shows up.
- CI's "headless config load" proves `config.lua` parses, nothing more.

Build a **fixture-driven file-opening test** with **two tiers that share one engine**:

| Tier | Command | Where it runs | Purpose |
|---|---|---|---|
| **e2e** | `make e2e` | Inside the Docker image (nvim 0.9.5, LunarVim 1.3, Mason servers baked in) | Hermetic, reproducible validation of the **pinned** runtime. **Strict**: every expected LSP binary is present in the image, so a missing attach is a *failure*, never a skip. It remains outside CI and `test-all` while the documented baseline is red; it becomes blocking only after the green follow-up. |
| **smoke** | `make smoke` (or `make deploy-smoke`) | On the **active system**: the real `~/.config/lvim` deploy, the real local `lvim`/nvim (0.11.x today), the real Mason/uv/brew tool state | The post-deploy feedback loop for the user (and for Claude after editing the config). **Tolerant of environment drift**: a missing LSP binary is reported as `skip(<bin> not installed)` and surfaced in the summary, not a failure. |

Both tiers open a committed corpus of representative files one by one and assert, per
file: no errors, correct filetype, highlighting active, expected LSP servers attached
and healthy, editing works, and (where configured) format-on-save works.

This plan was produced via the brainstorming skill (classified **architectural**:
new subsystem). A feasibility probe was run first; see "Probe findings" below.

## Objective

When complete:

1. `make deploy-smoke` is the one-command feedback loop on the active system. It exits
   non-zero with a readable table of **which fixture failed which check and why**.
1b. `make e2e` runs the same corpus inside the Docker image in strict mode. It is wired
   into CI only after the documented strict baseline is fully green.
2. Fixtures for every filetype the user regularly opens live in
   `tests/smoke/fixtures/` and are committed.
3. One engine (`runner.lua` + `manifest.lua` + `smoke.py`) serves both tiers; the only
   differences are the `--mode e2e|smoke` flag (strict vs tolerant), the target config
   dir, and where it executes.
4. `CLAUDE.md` instructs Claude to run the loop after any change to `config.lua`,
   `ftplugin/`, `ftdetect/`, `after/`, or `lsp-settings/`.
5. The documented strict baseline is reproduced by visible fixture/check reports, then
   fixed in a separately approved green follow-up.
6. Every production behavior in the runner, orchestrator, Make targets, Docker image,
   and config fixes is implemented with test-driven development: write one focused
   behavior test, run it to observe the expected failure, make the minimal change,
   rerun it green, then refactor while the relevant suite stays green.

## Problem Statement

The config is a layered system (Neovim version × LunarVim 1.3 pins × lazy-locked
plugins × Mason servers × our `config.lua`/`ftplugin`/`ftdetect`) and the only real
integration test is "open a file and see what explodes". That test is currently
performed manually, by the user, after deploy, one surprise at a time. There is no
regression corpus, so a fix for `.sh` can silently break `.yaml`, and a fix verified
on 0.9.5 can be broken on 0.11.

## Solution Approach

Approaches considered:

| | Approach | Verdict |
|---|---|---|
| A | Extend the testinfra/Docker suite with more parametrized cases | Rejected as the *only* path: Docker-only, slow, tests 0.9.5 but **not the local machine** where issues appear. |
| B | **Standalone headless Lua runner + fixture manifest, orchestrated by a `uv run` Python script, exposed as two tiers: `make e2e` (Docker, strict) and `make smoke` (active system, tolerant)** | **Recommended.** One engine, two environments, two contracts. Docker gives CI a hermetic pinned-runtime e2e; the local tier tests what the user actually runs. |
| C | More plenary specs | Rejected: plenary bootstrap mocks `lvim`; cannot observe LSP attach, lazy-loading, or real autocmds. |

**Design (B):**

```
tests/smoke/
├── manifest.lua          # fixture → expectations (ft, parser/syntax, lsp, format)
├── runner.lua            # runs inside `lvim --headless`; writes JSON report
└── fixtures/             # committed corpus (copied to a temp dir before each run)
    ├── shell/script.sh, shell/.zshrc
    ├── yaml/config.yaml, yaml/playbooks/site.yml, yaml/deployment.yaml
    ├── ini/settings.ini, ini/foo.service
    ├── ssh/.ssh/config           # path pattern `.*/%.ssh/config` must match
    ├── log/app.log
    ├── text/notes.txt
    ├── json/data.json, json/package.json, json/tsconfig.json (jsonc)
    ├── xml/pom.xml, xml/Info.plist
    ├── python/main.py, python/test_sample.py, python/pyproject.toml
    ├── make/Makefile
    ├── just/justfile, just/.justfile
    ├── markdown/README.md
    ├── toml/Cargo.toml
    ├── git/.gitignore
    ├── lua/init.lua
    └── docker/Dockerfile
script/smoke.py           # uv script: stage fixtures, run lvim, parse JSON, rich table, exit code
                          #   --mode smoke (default, tolerant)  |  --mode e2e (strict)
tests/unit/test_smoke.py  # unit tests for smoke.py (mode semantics, report parse, exit codes)
tests/testinfra/test_e2e.py    # e2e tier: runs `script/smoke.py --mode e2e` inside the Docker container
```

**Data flow:** `smoke.py` copies `tests/smoke/fixtures/` into a fresh temp dir
(so format-on-save writes never dirty the repo and `.ssh/config` path patterns
resolve), invokes
`lvim --headless -c "lua SMOKE_OUT='<tmp>/report.json'; SMOKE_ROOT='<tmp>'" -c "luafile tests/smoke/runner.lua" -c "qa!"`
under a timeout, reads `report.json`, renders a table, exits 0/1.

## Mandatory TDD Execution

The smoke suite must be built with strict red-green-refactor cycles. There is **no
production code before a focused test has failed for the intended reason**. "Production
code" here includes `script/smoke.py`, `tests/smoke/runner.lua`, `manifest.lua` behavior,
Make targets, Docker provisioning, and config changes that make a fixture pass.

For every new behavior:

1. **RED** — write one test with a name that states the regression it catches. Derive
   expected filetypes, statuses, messages, exit codes, and fixture content independently
   as literals; do not calculate them with the code under test. Run only that test and
   confirm it fails because the behavior is absent or wrong, not because of setup,
   collection, or a typo.
2. **GREEN** — make the smallest production change that makes that exact test pass.
   Rerun the focused test, then the affected unit or integration suite.
3. **REFACTOR** — only after green, remove duplication or improve names. Rerun the
   same tests and keep them green before beginning the next behavior.

Tests must exercise the script and runner through their real boundaries. Unit tests may
substitute only the external `lvim` process with a small executable test double that
writes a complete report; assertions must be on the script's staged files, arguments,
JSON, rendered result, and exit status--never calls on the double. Docker e2e tests run
the real LunarVim binary, deployed config, and fixture corpus. Tests must not grep
source text or assert private implementation details.

The implementation order is:

1. Start `tests/unit/test_smoke.py` with a subprocess contract test that invokes the
   missing `script/smoke.py` against a controlled stub `lvim`; it must initially fail
   at its assertion that a passing report produces a zero exit code and valid JSON.
   This avoids an import-time collection error while proving the public CLI contract.
2. Add one failing unit test at a time for staging dotfiles, `--only` forwarding,
   report parsing, smoke/e2e skip semantics, timeout handling, and missing-`lvim`
   exit code `2`; make each green with the minimal orchestrator implementation.
3. Add the fixture manifest and runner one observable check at a time. First create
   a failing e2e assertion for `opens`, then filetype, highlighting, LSP attachment,
   health, editing, and formatting. Each assertion must run the real headless runner
   and report its failing fixture/check pair before runner code is added.
4. For each discovered config regression, preserve the failing fixture assertion
   first, observe it red on the affected Neovim version, then make the smallest
   config or dependency change and prove that exact fixture green on both supported
   versions where it is in range.
5. Add Make, Docker, and CI wiring only after their behavior is covered by an
   executable test or a real `make e2e` invocation that has been observed to fail
   before the wiring and pass afterwards.

At the end of each cycle, mentally mutate the changed behavior (for example, reverse
the smoke/e2e missing-binary policy, omit a dotfile from staging, or report the wrong
filetype) and ensure at least one test would fail. Record the focused red and green
commands in the PR description; do not commit a test simply because it passes after
the implementation already exists.

### Intentional-red baseline and CI policy

This is the authoritative current baseline for the pinned Neovim 0.9.5 Docker runtime.
It was reconciled against an actual full `make e2e` report on 2026-08-21. The
testinfra contracts assert the runner's real report—not a process crash, missing JSON,
or opaque nonzero exit—as evidence for each outcome.

| Fixture(s) | Expected strict report | Why it remains in this baseline |
|---|---|---|
| `shell/script.sh` | `format=fail`; its classified runtime message includes `formatter=shfmt`, a formatting client, and `str_utfindex`. `opens`, `filetype`, `highlight`, `lsp`, `lsp_healthy`, and `edit` remain `pass`. | The 0.9.5 none-ls formatting path has a `str_utfindex`-type compatibility failure. |
| `yaml/playbooks/site.yml` | `lsp=fail` with `missing=ansiblels`; `lsp_healthy=pass`; `opens`, `filetype`, `highlight`, and `edit` remain `pass`. | The expected `ansiblels` client does not attach in the strict image. |
| `log/app.log` | `ft_got=""`; `filetype=fail` (`expected log, got`); `highlight=fail` (`builtin syntax=nil`); `opens` and `edit` remain `pass`. | The active filetype/syntax path does not establish the expected `log` type or its builtin syntax. |
| `text/notes.txt` | `filetype=pass` (`text`), but `highlight=fail` with `builtin syntax=nil`; `opens` and `edit` remain `pass`. | The expected builtin text syntax highlight is unavailable. |
| `lua/init.lua` | `opens=fail` and `highlight=fail`, each preserving an `invalid node type` error for language `lua`; `filetype` and `edit` remain `pass`. `format=fail` contains the none-ls `str_utfindex` discriminator. | The pinned Lua treesitter query/runtime is incompatible, and the same none-ls formatter path fails. |
| `just/justfile`, `just/.justfile` | Each produces only `version=skip`: `nvim version 0.9.5 is below minimum 0.10`. | These are legitimate, tested version-range skips, not failures; the fixtures are intentionally out of range on the pinned runtime. |

The failure rows—not the legitimate `just/*` skips—make strict `make e2e` nonzero.
They are a **pre-fix TDD baseline**, not a state that may be hidden, inverted, accepted
as a runner crash, whitelisted, or made green by relaxing checks. This baseline-only
change leaves active configuration, Docker provisioning, CI, and `test-all` unchanged.

The separately approved green follow-up must first use the focused fixture contracts to
resolve every failure row above: the none-ls formatter compatibility failure, the
`ansiblels` attachment failure, `log` filetype and syntax, text builtin syntax, and the
Lua treesitter and formatter failures. It must also revalidate that both `just/*`
fixtures retain their legitimate 0.9.5 version skips. Only after all in-range checks
pass, the full `make e2e` exits zero (with only those version skips), and the focused
contracts are made green without inverted assertions may that follow-up add `e2e` to
`test-all` and a blocking CI workflow step. It must not use `continue-on-error`.

TDD remains mandatory: each eventual runtime/config repair starts from a focused,
observed failing fixture check and ends green. A detection contract that passes while
asserting a known runtime `fail` is honest baseline evidence, not a fabricated red or
proof that the runtime regression is fixed.

**Per-fixture checks (runner.lua):**

| Check | How | Why |
|---|---|---|
| `opens` | `pcall(vim.cmd.edit)`; reset `vim.v.errmsg`; wrap `vim.notify`/`vim.api.nvim_err_writeln`; diff `:messages` before/after | Catches plugin crashes on `BufRead*`/`FileType` autocmds (e.g. none-ls on 0.11). |
| `filetype` | `vim.bo.filetype == expected` | Missing detection (`.log`, `.justfile`) |
| `highlight` | `vim.treesitter.highlighter.active[buf] ~= nil` when `parser` expected; else `vim.b.current_syntax ~= nil` for builtin-syntax fallbacks (`xml`, `sshconfig`, `log`) | Parser missing / highlighter never attached |
| `lsp` | `vim.wait(timeout, #get_clients({bufnr}) >= #expected)`; attached set ⊇ expected. **Mode-dependent**: in `smoke` mode a server whose binary is not `executable()` is `skip(<bin> not installed)`; in `e2e` mode it is a `fail` (the image must contain it). | LSP silently not attaching (the python custom-server `cmd` gotcha) |
| `lsp_healthy` | no client with `is_stopped()`; no `"server exited"`/`"rpc"` errors in messages | Server crash after attach |
| `edit` | `normal! ggOx`, `normal! u`, `startinsert`/`stopinsert` | Fires `InsertEnter`/`BufReadPost` lazy specs (lsp_signature, surround, leap, todo-comments) |
| `format` (only if fixture path matches `lvim.format_on_save.pattern`) | `:w` on the temp copy, then `vim.lsp.buf.format({async=false, timeout_ms})`; assert no error and buffer == `fixture.formatted` sibling if provided | Formatter wiring (shfmt/stylua via none-ls, ruff/taplo/jsonls via LSP) |

Each check yields `pass | fail | skip` with a message; a fixture fails if any check
fails. `skip` reasons are printed so "passed" never hides "not actually tested".

**Version-conditional expectations:** manifest entries may carry `min_nvim = "0.10"`
/ `max_nvim`; the runner evaluates them, so the same manifest is correct on 0.9.5
(Docker e2e) and 0.11.x (local smoke). Version skips are legitimate in **both** modes.

**Mode semantics (`SMOKE_MODE` global, set by `smoke.py --mode`):**

| Situation | `smoke` (active system) | `e2e` (Docker) |
|---|---|---|
| LSP binary missing | `skip`, counted + listed in summary | `fail` |
| Formatter binary missing | `skip` | `fail` |
| Fixture outside nvim version range | `skip` | `skip` |
| Any error on open / wrong ft / no highlight / client crashed | `fail` | `fail` |
| Config dir | `~/.config/lvim` (deployed) or `--target` | `/root/.config/lvim` (synced at image build) |
| Exit 0 requires | no `fail` | no `fail` **and** zero non-version skips |

**Headless gotchas (from the probe) the runner must handle:**

- Set `vim.o.lines = 50; vim.o.columns = 160` **before** opening anything — under
  `--headless` the window is 0-high and a `BufWinEnter *` autocmd raises
  `E36: Not enough room`, aborting every later autocmd (false negatives everywhere).
- `io.write` to stdout is unreliable under headless; **always write the report to a
  file** (`SMOKE_OUT`).
- Give LSP attach a real timeout (3–5 s per server; `yamlls`/`basedpyright` are slow
  on cold start) and cap total runtime (`smoke.py --timeout`, default 180 s).
- Run with `--headless` **and** `-u`-free (we want the *deployed* `~/.config/lvim`
  config, not a minimal init). Allow `--target DIR` to point at a different config dir
  (`LUNARVIM_CONFIG_DIR`) for testing the repo checkout without deploying.

## Probe findings (2026-08-21, local nvim 0.11.3, `lvim` 1.3)

A throwaway version of `runner.lua` was run against 14 scratch files. The suite
should reproduce all of these on first run:

1. **none-ls crash on every LSP-attached buffer** —
   `none-ls.nvim/lua/null-ls/client.lua:51: attempt to index field '_request_name_to_capability' (a nil value)`.
   The lazy-locked none-ls is from 2023-11-29; nvim 0.11 removed that private
   field. Fix belongs in `config.lua` (pin a newer none-ls commit, with a 0.9.5
   compatibility check in Docker) — **out of scope for this plan, tracked as the
   suite's first red test.**
2. **`*.justfile` and `*.log` → `filetype=""`** (no detection). `after/syntax/log.vim`
   exists in the repo but nothing sets `ft=log`. Fix: `vim.filetype.add` entries in
   `config.lua` (`just`/`justfile`/`.justfile` → `just`, `*.log` → `log`).
3. **`E36: Not enough room`** from a `BufWinEnter *` autocmd under headless (see
   gotchas). Runner-side mitigation; may also hide a plugin issue worth investigating.
4. Observed LSP attach (good baseline for the manifest): `sh→bashls,null-ls`,
   `python→basedpyright,ruff`, `yaml→yamlls`, `json→jsonls`, `toml→taplo`,
   `text→vale_ls`; `xml`, `markdown`, `make`, `gitignore`, `dosini`, `sshconfig` → none.

## Relevant Files

- `config.lua` — the active config: `format_on_save.pattern`, `vim.filetype.add`
  rules, treesitter `ensure_installed`, LSP skip list, plugin specs. The manifest's
  expectations are derived from here; fixes for probe findings land here.
- `ftplugin/{sh,python,yaml,json,toml,dockerfile,go}.lua` — hand-configured LSP
  servers; tell us which `lsp` names to expect per filetype.
- `after/syntax/log.vim`, `after/ftplugin/make.vim` — existing fallback syntax/ftplugin
  files that fixtures should exercise.
- `tests/testinfra/conftest.py` — `host` / `run_lua` fixtures; pattern for running
  Lua inside the container (base64 → `/tmp/probe.lua` → `luafile`). `test_smoke.py`
  reuses `host`.
- `tests/testinfra/test_filetypes.py` — current, narrower filetype checks; keep, but
  the new suite supersedes its coverage.
- `tests/unit/test_install.py`, `tests/unit/conftest.py` — style precedent for unit
  tests of a `uv run` script.
- `script/install.py`, `script/doctor.py` — precedent for PEP 723 `uv run` scripts
  with `rich` tables and exit-code contracts; `smoke.py` mirrors them.
- `Makefile` — add `smoke`, `deploy-smoke`, and `e2e` targets; defer wiring strict
  `e2e` (not active-system `smoke`) into `test-all` until the separately approved
  green follow-up resolves every enumerated strict baseline.
- `Dockerfile` — already `COPY . .` so fixtures are in the image; ensure
  `TSInstallSync` list covers parsers the manifest expects (`make`, `markdown`,
  `gitignore`, `xml` is N/A on 0.9).
- `.github/workflows/ci.yml` — defer the `docker-validate` job's blocking strict
  `make e2e` step until the separately approved green follow-up resolves every
  enumerated strict baseline.
- `CLAUDE.md` — document the feedback loop.
- `specs/install.md` — cross-link: deploy → smoke.
- `pyproject.toml` — `testpaths` currently only `tests/testinfra`; `test-unit` passes
  the path explicitly, so no change needed unless adding `tests/unit`.

### New Files

- `tests/smoke/manifest.lua` — list of `{ path, ft, parser | syntax, lsp, format, min_nvim, note }`.
- `tests/smoke/runner.lua` — headless check runner, JSON report writer.
- `tests/smoke/fixtures/**` — committed corpus (see tree above; ~22 small files,
  each with a one-line header comment stating what it exercises where the format
  allows comments).
- `tests/smoke/fixtures/**/*.formatted` (optional, phase 3) — golden outputs for
  format checks (`script.sh.formatted`, `init.lua.formatted`, `main.py.formatted`).
- `script/smoke.py` — orchestrator (`uv run script/smoke.py [--target DIR] [--only GLOB] [--timeout N] [--json] [--keep] [--verbose]`).
- `tests/unit/test_smoke.py` — unit tests for `smoke.py`.
- `tests/testinfra/test_e2e.py` — runs the suite in the Docker image.

## Implementation Phases

### Phase 1: TDD foundation — unit contracts, fixtures, manifest + runner (red on purpose)

Begin with the CLI contract tests in `tests/unit/test_smoke.py`; run each test red
before adding the smallest `smoke.py` behavior needed to make it green. Commit the
fixture corpus and a manifest describing what *should* happen. For every runner check,
write its real-runner e2e assertion first, observe the expected failure, then implement
only `opens`, `filetype`, `highlight`, or `lsp` behavior needed for that assertion.
Run the runner by hand against the local deploy; confirm it reports the documented
baseline findings as failures. No config fixes yet — the suite must prove it can see
the bugs.

### Phase 2: TDD core — `script/smoke.py` + Make targets + unit tests

Finish the orchestrator in test-first slices: staging, argument handling, report
parsing, exit-code mapping, skip accounting, timeout, table rendering, and JSON
output. Each slice begins with the focused failing unit test and ends with it green.
Then add `make smoke` and `make deploy-smoke`; use the real command's before/after
result as the red/green evidence for each target.

### Phase 3: TDD integration & polish — Docker, format checks, docs, then CI

`tests/testinfra/test_e2e.py` runs `uv run script/smoke.py --json` in the
container. Add `edit` and `format` checks + golden files test-first, using golden
outputs derived by hand rather than by the formatter under test. Update `CLAUDE.md`
and `specs/install.md`. Then (separate PRs) fix the probe findings through their
already-red fixture tests and watch the suite go green on both 0.9.5 and 0.11. Add the
blocking CI step only after the strict Docker e2e command is green, per the
intentional-red baseline policy.

## Step by Step Tasks

IMPORTANT: Execute every step in order, top to bottom.

### 0. Establish the TDD baseline before implementation

- Create `tests/unit/test_smoke.py` before creating `script/smoke.py`. Its first test
  invokes the public CLI as a subprocess with a controlled temporary `lvim` executable
  that writes a complete, hand-authored passing report. Assert observable behavior:
  a zero exit code and valid JSON output. Run it and confirm it fails at the assertion
  because `script/smoke.py` does not exist; it must not fail during pytest collection.
- Implement only enough of `script/smoke.py` to pass that test. Rerun the focused test
  green, then refactor only if needed while it remains green.
- Before adding each later behavior, name the production change that would make its
  test fail. Reject tests that only detect source-text changes, check a mock's calls,
  or derive their expected values from the code being tested.
- Preserve command output for every red and green cycle. A test that passes on its
  first execution does not count as TDD; correct or replace it before proceeding.

### 1. Create the fixture corpus

- Create `tests/smoke/fixtures/` with the tree in "Solution Approach". Each file is
  small (5–30 lines), realistic, and **deliberately exercises** something:
  - `shell/script.sh`: shebang, `set -euo pipefail`, a function, a `[[ ]]` test, one
    intentionally mis-indented block (for the format check); `shell/.zshrc`: `ft=zsh`.
  - `yaml/config.yaml`: anchors + multi-doc; `yaml/playbooks/site.yml`: must detect
    `yaml.ansible`; `yaml/deployment.yaml`: a k8s Deployment (schema match in
    `ftplugin/yaml.lua`).
  - `ini/settings.ini` (`dosini`), `ini/foo.service` (`systemd`).
  - `ssh/.ssh/config` (`sshconfig`, builtin syntax).
  - `log/app.log`: mixed `INFO/WARN/ERROR` lines, timestamps (exercises
    `after/syntax/log.vim`).
  - `text/notes.txt` (`text`; vale_ls if installed).
  - `json/data.json`, `json/package.json` (schemastore), `json/tsconfig.json` (`jsonc`,
    comments + trailing comma).
  - `xml/pom.xml`, `xml/Info.plist` (`xml`, builtin syntax).
  - `python/main.py` (imports, a dataclass, an unused import for ruff), `python/test_sample.py`
    (pytest style for neotest), `python/pyproject.toml` (root marker for `ftplugin/python.lua`).
  - `make/Makefile` (tabs, `.PHONY`, `$(shell)`), `just/justfile`, `just/.justfile`.
  - `markdown/README.md` (fenced code blocks in 3 languages → `markdown_inline` injections).
  - `toml/Cargo.toml`, `git/.gitignore`, `lua/init.lua` (a `require`, a table, mis-formatting
    for stylua), `docker/Dockerfile`.
- Add `tests/smoke/fixtures/README.md` explaining: "these are opened by
  `make smoke`; add a file here whenever a filetype bites you."
- Ensure `.gitignore` does not exclude any fixture (it ignores `*.zip`, `*.so`, etc. —
  check `.log`, `.ini`, and dotfiles are not ignored; add negations if needed).
- Ensure `.dockerignore` does not exclude `tests/`.
- Treat each fixture plus its literal manifest expectation as a regression test. Add
  the fixture and the assertion that opens it before the behavior it requires. For
  known broken cases, capture and retain the observed red report as the baseline.

### 2. Write `tests/smoke/manifest.lua`

- Return a list of entries:

  ```lua
  return {
    { path = "shell/script.sh", ft = "sh", parser = "bash", lsp = { "bashls" }, format = "shfmt" },
    { path = "shell/.zshrc", ft = "zsh", parser = "bash", lsp = { "bashls" } },
    { path = "yaml/playbooks/site.yml", ft = "yaml.ansible", parser = "yaml", lsp = { "ansiblels" } },
    { path = "ssh/.ssh/config", ft = "sshconfig", syntax = true },
    { path = "log/app.log", ft = "log", syntax = true },
    { path = "just/justfile", ft = "just", syntax = true, min_nvim = "0.10" },
    { path = "xml/Info.plist", ft = "xml", syntax = true },
    { path = "python/main.py", ft = "python", parser = "python", lsp = { "basedpyright", "ruff" }, format = "ruff" },
    -- ...
  }
  ```

- Fields: `path` (relative to fixtures root), `ft` (required), exactly one of
  `parser` (treesitter highlighter must be active) or `syntax` (builtin
  `b:current_syntax` must be set), `lsp` (list; each asserted only if its binary —
  looked up via a small `lsp_bins` map, e.g. `bashls → bash-language-server`,
  `basedpyright → basedpyright-langserver`, `yamlls → yaml-language-server`,
  `jsonls → vscode-json-language-server`, `taplo`, `ruff`, `ansiblels → ansible-language-server`,
  `vale_ls → vale-ls` — is executable, else `skip`), `format` (formatter name; only
  checked when the fixture path matches `lvim.format_on_save.pattern`), `min_nvim` /
  `max_nvim`, `note`.
- Expectations are **derived from `config.lua` as it is today**, not from the ideal;
  for the known gaps (`log`, `just`), encode the *desired* `ft` so they fail until fixed.

### 3. Write `tests/smoke/runner.lua`

- Add the e2e assertion for one check before its implementation. The initial assertion
  must expose that check as missing or wrong in the JSON report, not merely assert that
  a Lua function exists. Start with `opens`, then add `filetype`, `highlight`, `lsp`,
  `lsp_healthy`, `edit`, and `format` in that order.
- Read `SMOKE_ROOT` (staged fixtures dir) and `SMOKE_OUT` (JSON path) globals;
  fall back to `tests/smoke/fixtures` + `/tmp/smoke-report.json` when run manually.
- Before anything: `vim.o.lines = 50; vim.o.columns = 160; vim.o.more = false;
  vim.o.swapfile = false; vim.o.confirm = false`.
- Install message capture: wrap `vim.notify` (record `level >= WARN`), wrap
  `vim.api.nvim_err_writeln`/`nvim_echo` with `err=true`, and snapshot
  `vim.api.nvim_exec2("messages", {output=true}).output` before/after each fixture.
- For each manifest entry (skip if nvim version outside `[min_nvim, max_nvim]`):
  1. `opens` — reset `vim.v.errmsg`, `pcall(vim.cmd.edit, abs_path)`, `vim.wait(300)`.
     Fail on pcall error, non-empty `errmsg`, or new `E\d+`/`Error`/`stack traceback`
     lines in captured messages.
  2. `filetype` — compare `vim.bo.filetype`.
  3. `highlight` — if `parser`: wait ≤1 s for `vim.treesitter.highlighter.active[buf]`;
     also record `require("nvim-treesitter.parsers").has_parser(parser)` in the message
     so "parser missing" vs "highlighter not attached" are distinguishable. If
     `syntax`: assert `vim.b[buf].current_syntax ~= nil` (wait ≤500 ms).
  4. `lsp` — compute `want = filter(lsp, executable)`; `vim.wait(5000, all attached)`;
     fail listing missing names; `skip` listing non-executable names. Then
     `lsp_healthy`: no `c.is_stopped()`; no `server exited|rpc|Client \d+ quit` in new
     messages.
  5. `edit` — `vim.cmd "normal! ggOsmoke"`, `vim.cmd "normal! u"`, `vim.cmd.startinsert()`,
     `vim.cmd.stopinsert()`; fail on new error messages.
  6. `format` — only if `format` set **and** path matches a glob in
     `lvim.format_on_save.pattern` (use `vim.fn.glob2regpat`): `vim.cmd "silent write"`,
     `vim.lsp.buf.format { async = false, timeout_ms = 5000, bufnr = buf }`; fail on
     error; if `<path>.formatted` exists, compare buffer lines to it.
  7. `vim.cmd "silent! bwipeout!"` and, after every fixture, `collectgarbage()`.
- Write `{ nvim = "0.11.3", lvim_config = stdpath("config"), results = { { path, ft_got,
  checks = { { name, status, message } } } } }` to `SMOKE_OUT` via `io.open`.
  Never rely on stdout.
- Wrap the whole run in `pcall`; on an unexpected runner error still write a JSON with
  `runner_error`, so `smoke.py` can print it instead of "no report".

### 4. Write `script/smoke.py`

- Follow the tests from step 0 in narrow red-green-refactor slices: staging, execution,
  report parsing, display, mode policy, timeout, and cleanup. Do not add a later
  branch until its own failing test exists and has been observed.
- PEP 723 header (`rich>=13.0`), same style as `install.py`/`doctor.py`.
- Args: `--mode smoke|e2e` (default `smoke`; exported to the runner as `SMOKE_MODE`;
  `e2e` makes missing binaries failures and fails the run on any non-version skip),
  `--target DIR` (config dir → exported as `LUNARVIM_CONFIG_DIR`; default unset
  = deployed `~/.config/lvim`), `--lvim PATH` (default `lvim` on `PATH`, fallback
  `~/.local/bin/lvim`), `--only GLOB` (filter manifest paths; passed through as
  `SMOKE_ONLY`), `--timeout N` (default 180), `--json` (print report JSON only, for
  Claude/CI), `--keep` (don't delete the staging dir; print its path).
- Stage: `tempfile.mkdtemp(prefix="lvim-smoke-")`, `shutil.copytree(fixtures, tmp/fixtures)`.
- Run: `subprocess.run([lvim, "--headless", "-c", f"lua SMOKE_ROOT={root!r}; SMOKE_OUT={out!r}; SMOKE_ONLY={only!r}", "-c", f"luafile {runner}", "-c", "qa!"], timeout=…, capture_output=True)`.
  On `TimeoutExpired` → exit 1 with "runner hung (likely LSP wait) — rerun with --keep".
- Render: rich table `Fixture | ft | opens | filetype | highlight | lsp | edit | format`
  with ✔/✘/– and a second table of failure messages. Summary line
  `N fixtures, P passed, F failed, S skipped-checks`.
- Exit codes: `0` all pass; `1` any fail / runner error / timeout; `2` bad args /
  `lvim` not found (mirror `install.py`'s contract).
- Print the raw stderr of `lvim` only when `--verbose` or on runner error.

### 5. Makefile + docs

- First run the proposed command directly and capture its failing result; then add the
  target and verify the same behavior through `make`. The Make targets must invoke the
  real script rather than a mocked substitute.
- `smoke: ## Smoke-test the ACTIVE system: open every fixture with the deployed ~/.config/lvim and local lvim` → `@uv run script/smoke.py --mode smoke $(ARGS)`.
- `deploy-smoke: deploy smoke ## Deploy then smoke-test the active system`.
- `e2e: docker-build ## E2E (strict) file-opening tests inside the pinned 0.9.5 Docker image` → `docker run --rm lunarvim-config:test uv run script/smoke.py --mode e2e $(ARGS)`.
- Add `smoke`, `deploy-smoke`, `e2e` to `.PHONY`. `smoke` is deliberately **not** in
  `test-all` because it depends on the developer's machine state; it is the post-deploy
  loop. Add strict `e2e` to `test-all` only in the green follow-up that resolves every
  known baseline failure; otherwise `test-all` would intentionally fail.
- `CLAUDE.md`: under Testing add `make smoke` (active system) and `make e2e` (Docker),
  and a new "Feedback loop" paragraph:
  *after editing `config.lua`, `ftplugin/`, `ftdetect/`, `after/`, or `lsp-settings/`,
  run `make deploy-smoke`; if a filetype breaks, first add/adjust a fixture +
  manifest entry so the failure is reproduced, then fix via a red-green-refactor
  cycle.* Also add to Gotchas: headless `E36` / `io.write` notes.
- `specs/install.md`: one line linking deploy → `make smoke`.

### 6. Unit tests — `tests/unit/test_smoke.py`

- Start at the CLI boundary with the subprocess test from step 0. Once the script
  exists, importing it the same way `test_install.py` does is allowed for pure helpers,
  but command contracts remain subprocess tests.
- Test: staging copies dotfiles (`.ssh/config`, `.zshrc`, `.gitignore`, `.justfile`).
- Test: report parsing → exit code mapping (all pass → 0; one fail → 1; `runner_error` → 1;
  missing report → 1).
- Test: `--only` filter string is passed through; `--lvim` missing → exit 2.
- Test: mode semantics — a report with a `skip(not installed)` check exits 0 in
  `--mode smoke` and 1 in `--mode e2e`; a `skip(nvim < 0.10)` exits 0 in both.
- Test: table rendering doesn't crash on `skip`-only fixtures (use a fake report).
- Use a stub `lvim` (a tiny shell script that writes a complete, canned JSON to
  `$SMOKE_OUT` parsed from argv) so the unit suite never needs Neovim. Assert the
  actual staged files, CLI output, JSON, and exit status rather than the stub's calls.

### 7. Docker e2e tier / CI integration

- `tests/testinfra/test_e2e.py`: `host.run("cd /root/lunarvim-config && uv run script/smoke.py --mode e2e --json")`,
  assert `rc == 0`, and on failure print the JSON. Uses the same session `host`.
- First run this test against the real image and observe it fail before adding the
  missing image provision, runner behavior, or config fix needed to pass it. Do not
  mock LunarVim, Mason, or the runner in this tier.
- Because e2e is strict, the `Dockerfile` must install every binary the manifest
  expects for fixtures that are in range on 0.9.5: add `ansible-language-server` and
  `vale` (+`vale-ls` if kept in the manifest) to the `MasonInstall` line, or drop
  those servers from the manifest with a `note` — but never let e2e pass via skip.
- `Dockerfile`: extend `TSInstallSync` with `make markdown markdown_inline gitignore
  git_config` (already in `ensure_installed`; the image just hadn't precompiled them).
  Confirm `uv` is on `PATH` in the image (it is: `/usr/local/bin/uv`).
- `.github/workflows/ci.yml` `docker-validate`: add step
  `docker run --rm lunarvim-config:test uv run script/smoke.py --mode e2e` only after
  all in-range strict e2e fixtures are green. The initial intentional-red baseline
  must never be converted into a passing CI step through an allow-failure setting,
  inverted assertion, or skip.

### 8. Validate the suite sees the known bugs, then fix them test-first

- Run `make deploy-smoke` locally (nvim 0.11.3): expect failures for none-ls
  (`opens` on every LSP-attached fixture), `log/app.log` + `just/*` (`filetype`).
- Run `make e2e` (0.9.5): expect exactly the strict baseline in
  [Intentional-red baseline and CI policy](#intentional-red-baseline-and-ci-policy):
  failures are visible and `just/*` is version-skipped. Do not accept any additional
  failure, non-version skip, runner error, or missing report as baseline evidence.
- Record the failing fixture list in the PR description. Each follow-up begins by
  rerunning its affected fixture red, applies the smallest fix, and proves the
  fixture green in its focused run and relevant full tier. The final follow-up must
  make `make e2e` green before it adds the blocking CI step.
- Run `make test-unit`, `luacheck tests/smoke --globals lvim vim SMOKE_ROOT SMOKE_OUT SMOKE_ONLY`
  (or `make docker-lint`), `stylua --check tests/smoke`.

## Testing Strategy

- **Unit** (`tests/unit/test_smoke.py`): orchestrator logic with a stub `lvim`; fast,
  no Neovim required; runs in the existing `test-unit` target and CI.
- **Smoke tier, active system** (`make smoke` / `make deploy-smoke`): against the
  deployed config on the developer's nvim and real tool state. Tolerant of missing
  binaries (reported, not failed). This is the user-facing feedback loop.
- **E2E tier, Docker** (`make e2e`, `tests/testinfra/test_e2e.py`, CI): same runner
  inside the 0.9.5 image in strict mode; guarantees the version-duality rule in
  `CLAUDE.md` is actually enforced and that the image is a faithful target.
- **Lint**: `luacheck`/`stylua` over `tests/smoke/*.lua`; `ruff` over `script/smoke.py`.
- **Edge cases covered by design**: LSP binary absent (skip, not fail); nvim-version
  conditional fixtures; runner crash still yields a report; LSP hang → timeout with
  actionable message; fixtures with dotfile names survive staging; format check never
  touches repo files.
- **TDD evidence**: every behavior test is run red before its implementation and green
  after it; focused commands are recorded with the change. Tests assert independently
  derived, user-visible behavior through the CLI or real runner, not source text or
  mock interactions. The initial regression baseline is intentionally red, while the
  CI-enabled final state is entirely green.
- **Self-check of the checker**: a deliberately broken manifest entry (`ft = "nope"`)
  run via `--only` must produce a `filetype` failure — do this once manually in step 8
  and note it in the PR.

## Acceptance Criteria

- [ ] `tests/smoke/fixtures/` contains at least one fixture for each of: sh, zsh, yaml,
      yaml.ansible, ini/dosini, systemd, sshconfig, log, text, json, jsonc, xml, plist,
      python, Makefile, justfile, markdown, toml, gitignore, lua, Dockerfile.
- [ ] `make smoke` runs against `~/.config/lvim` with the host `lvim`, prints a per-fixture
      table, exits non-zero on any failure, and lists skipped-because-not-installed
      servers with install hints; total runtime < 3 minutes locally.
- [ ] `make e2e` runs the same corpus inside the Docker image in strict mode (missing
      binaries = failure) and exits non-zero on any failure or non-version skip.
- [ ] Every check reports `pass|fail|skip` with a message; skipped LSP checks name the
      missing binary.
- [ ] `make deploy-smoke` exists. After the strict suite is green, `make test-all`
      includes `e2e` (not active-system `smoke`).
- [ ] `uv run script/smoke.py --json` emits machine-readable output usable by Claude/CI.
- [ ] `tests/testinfra/test_e2e.py` runs the identical runner inside the Docker
      image; CI `docker-validate` runs `--mode e2e` only after the strict suite is
      green.
- [ ] `tests/unit/test_smoke.py` passes without Neovim installed.
- [ ] Before config fixes, strict e2e reports exactly the current failures and
      version skips in [Intentional-red baseline and CI
      policy](#intentional-red-baseline-and-ci-policy), with a per-fixture check,
      status, and discriminator. After each fix, the corresponding focused test is
      observed green; strict e2e is fully green before its CI step is enabled.
- [ ] No production behavior is added without a focused test that was first observed
      failing for the intended reason; no test relies on source-text inspection or
      mock-interaction assertions.
- [ ] `CLAUDE.md` documents the `make deploy-smoke` loop and the headless gotchas.
- [ ] `luacheck`, `stylua --check`, and `ruff check script/smoke.py` are clean.

## Validation Commands

- `uv run script/smoke.py --help` — orchestrator parses args.
- `make deploy ARGS=--dry-run && make deploy && make smoke` — the full loop on the local machine (expect red for the known bugs until the follow-up fixes land).
- `uv run script/smoke.py --only 'shell/*' --keep` — filtered run; inspect staging dir.
- `uv run script/smoke.py --json | python3 -m json.tool` — machine-readable report is valid JSON.
- `make test-unit` — unit tests for `smoke.py` pass.
- `make e2e` — strict Docker e2e tier. Before config fixes, it must reproduce only the
  documented baseline; before CI is enabled, it must be green with only legitimate
  version skips and zero missing-binary skips.
- `make test-testinfra` — Docker suite including `test_e2e.py`.
- `luacheck tests/smoke --globals lvim vim SMOKE_ROOT SMOKE_OUT SMOKE_ONLY && stylua --check tests/smoke` — Lua lint/format (or `make docker-lint`).
- `uv run ruff check script/smoke.py` — Python lint.
- `git status --porcelain` after `make smoke` — empty: the suite never dirties the repo.

## Notes

- **Image attached to the request** rendered as a blank PNG placeholder; the specific
  error it showed could not be read. The probe independently surfaced the none-ls
  0.11 crash, which is the most likely candidate — confirm against the screenshot when
  implementing.
- No new Python dependencies: `rich` is already in the dev group and in the PEP 723
  headers. If `pytest` discovery should include `tests/unit` by default, add it to
  `testpaths` in `pyproject.toml` (optional).
- Keep `tests/testinfra/test_filetypes.py`; it is cheap and the two suites overlap only
  on `&filetype`. Consider folding it into the manifest later.
- The manifest intentionally lives in Lua (not JSON) so it can express
  `only_if_executable` and version guards without a second parser; `smoke.py` never
  reads it directly — it only reads the runner's JSON report.
- The approved green follow-up scope is defined once in
  [Intentional-red baseline and CI policy](#intentional-red-baseline-and-ci-policy).
  It resolves every in-range strict failure there, preserves the legitimate `just/*`
  version skips, then enables `test-all` and CI only after a zero-exit `make e2e`.
