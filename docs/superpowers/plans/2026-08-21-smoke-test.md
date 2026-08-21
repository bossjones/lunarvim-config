# LunarVim Smoke Test Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build one fixture-driven file-opening engine that reports active-system smoke regressions and captures strict Docker e2e findings as a testable red baseline.

**Architecture:** `script/smoke.py` stages committed fixtures and invokes the active LunarVim configuration with `tests/smoke/runner.lua`. The Lua runner loads `manifest.lua`, opens each fixture, writes a JSON report, and applies smoke/e2e policy. Python owns CLI parsing, process timeout, report validation, rendering, and exit codes; Docker/testinfra exercise the same public CLI against the real 0.9.5 image.

**Tech Stack:** Python 3.10+ with PEP 723 and Rich, Lua compatible with Neovim 0.9.5 and 0.11+, LunarVim 1.3, pytest/testinfra, Docker, GNU Make.

**Spec:** `specs/smoke-test.md`

## Global Constraints

- Support the active local LunarVim runtime and the Docker-pinned Neovim 0.9.5; guard 0.10+-only APIs and use compatibility helpers where necessary.
- Follow strict TDD for every production behavior: focused test red for the intended reason, minimal implementation green, then refactor with the relevant suite green.
- Tests assert real CLI/runner behavior and independently derived literals; never assert source text or test-double call counts.
- `smoke` tolerates missing LSP/formatter binaries as reported skips; `e2e` treats them as failures. Version-range skips are allowed in both modes.
- Never write format edits into the repository: copy fixtures to a fresh temporary directory for each invocation.
- Emit the authoritative runner report to `SMOKE_OUT`; headless stdout is diagnostic only.
- Keep the initial none-ls, `.log`, and `justfile` findings visibly red. Do not add a blocking CI e2e command until the follow-up fixes make all in-range strict checks green.
- Use existing `rich>=13.0`; do not add Python dependencies.

---

## File Structure

| Path | Responsibility |
|---|---|
| `script/smoke.py` | CLI, fixture staging, LunarVim invocation, report validation/rendering, and exit policy. |
| `tests/unit/conftest.py` | Loads `script/smoke.py` as the `smoke` fixture without packaging the script. |
| `tests/unit/test_smoke.py` | Fast subprocess and pure-helper contracts using a controlled executable `lvim` double. |
| `tests/smoke/fixtures/**` | Realistic, committed input corpus; never opened in place by the runner. |
| `tests/smoke/manifest.lua` | Literal fixture expectations: filetype, highlighting path, LSPs, formatter, and version bounds. |
| `tests/smoke/runner.lua` | Real headless LunarVim engine that emits check-level JSON results. |
| `tests/testinfra/test_e2e.py` | Docker integration contracts for valid reports, strict mode, and initially known red findings. |
| `.gitignore` / `.dockerignore` | Explicitly retain smoke fixture `.log` files and include `tests/` in the Docker build context. |
| `Makefile` | `smoke`, `deploy-smoke`, and strict Docker `e2e` entry points. |
| `Dockerfile` / `tests/testinfra/test_binaries.py` | Provision and assert every in-range strict-runtime parser and LSP binary. |
| `CLAUDE.md` / `specs/install.md` | Document the post-deploy feedback loop and headless constraints. |
| `.github/workflows/ci.yml` | Remains unchanged in this baseline implementation; a separate green follow-up adds strict e2e. |

## Shared Interfaces

| Python function | Contract |
|---|---|
| `parse_args(argv)` | Returns parsed `--mode`, `--target`, `--lvim`, `--only`, `--timeout`, `--json`, `--keep`, and `--verbose` values. |
| `stage_fixtures(source, staging_root)` | Copies `source` into `staging_root / "fixtures"` and returns that destination. |
| `build_lvim_command(lvim, runner, fixture_root, report_path, only)` | Returns the `lvim --headless` argv that assigns `SMOKE_ROOT`, `SMOKE_OUT`, and `SMOKE_ONLY` before `luafile runner`. |
| `runner_env(args)` | Returns a copy of `os.environ` with `SMOKE_MODE`; adds `LUNARVIM_CONFIG_DIR` only when `args.target` is non-empty. |
| `load_report(path)` | Returns decoded report JSON or raises `ValueError` when no valid report exists. |
| `report_exit_code(report, mode)` | Returns `0` or `1` according to report failures and mode-specific skip policy. |
| `render_report(report, console)` | Writes the fixture/check table, failure details, and skip summary to a Rich console. |
| `main(argv)` | Runs the complete CLI contract and returns an integer process exit code. |

```lua
-- tests/smoke/manifest.lua returns the literal entry list specified in Task 3.
-- Every entry has path and ft, exactly one of parser or syntax, and optional
-- lsp, format, min_nvim, max_nvim, and note fields.

-- tests/smoke/runner.lua output schema
{
  nvim = "0.9.5",
  lvim_config = "/root/.config/lvim",
  results = {
    {
      path = "shell/script.sh",
      ft_got = "sh",
      checks = { { name = "opens", status = "pass", message = "" } },
    },
  },
  runner_error = nil,
}
```

### Task 1: Establish the public smoke CLI contract

**Files:**
- Create: `tests/unit/test_smoke.py`
- Modify: `tests/unit/conftest.py`
- Modify: `tests/smoke/fixtures/shell/script.sh`
- Create: `script/smoke.py`

**Interfaces:**
- Produces: `main(argv) -> int`, `parse_args(argv) -> argparse.Namespace`, and a subprocess-compatible CLI.
- Consumes: `--lvim PATH`, `--json`, and the `SMOKE_OUT` global contract passed to LunarVim.

- [ ] **Step 1: Add the `smoke` module fixture and its smallest shell test input without creating production code**

```python
# tests/unit/conftest.py
SMOKE_PY = REPO_ROOT / "script" / "smoke.py"

@pytest.fixture(scope="session")
def smoke():
    spec = importlib.util.spec_from_file_location("lvim_smoke", SMOKE_PY)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
```

- [ ] Create the committed input needed by the subprocess contract:

```sh
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' smoke
```

- [ ] **Step 2: Write the failing subprocess behavior test**

```python
def test_cli_prints_passing_json_report_from_lvim(tmp_path: Path):
    lvim = write_lvim_stub(
        tmp_path,
        {"results": [{"path": "shell/script.sh", "checks": [
            {"name": "opens", "status": "pass", "message": ""},
        ]}]},
    )
    result = subprocess.run(
        ["uv", "run", "script/smoke.py", "--lvim", str(lvim), "--json"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["results"][0]["path"] == "shell/script.sh"
```

- [ ] **Step 3: Run the test and verify RED**

Run: `uv run pytest tests/unit/test_smoke.py::test_cli_prints_passing_json_report_from_lvim -v`

Expected: the assertion fails because `script/smoke.py` does not exist; pytest collection itself succeeds.

- [ ] **Step 4: Implement the minimal CLI, staging, and JSON output path**

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["rich>=13.0"]
# ///

def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    with tempfile.TemporaryDirectory(prefix="lvim-smoke-") as raw_root:
        root = Path(raw_root)
        fixture_root = stage_fixtures(FIXTURES_DIR, root)
        report_path = root / "report.json"
        completed = subprocess.run(
            build_lvim_command(Path(args.lvim), RUNNER, fixture_root, report_path, args.only),
            capture_output=True, text=True, timeout=args.timeout, env=runner_env(args),
        )
        report = load_report(report_path)
        if args.json:
            print(json.dumps(report, sort_keys=True))
        return report_exit_code(report, args.mode)
```

Implement this test utility in `tests/unit/test_smoke.py`; it simulates only the external
process boundary and writes a complete report:

```python
def write_lvim_stub(tmp_path: Path, report: dict[str, object]) -> Path:
    stub = tmp_path / "lvim"
    stub.write_text(
        "#!/usr/bin/env python3\n"
        "import json, re, sys\n"
        "command = next(arg for arg in sys.argv if 'SMOKE_OUT=' in arg)\n"
        "match = re.search(r\"SMOKE_OUT=['\\\"]?([^;'\\\"]+)\", command)\n"
        "assert match, command\n"
        f"with open(match.group(1), 'w', encoding='utf-8') as fh: json.dump({report!r}, fh)\n",
        encoding="utf-8",
    )
    stub.chmod(0o755)
    return stub
```

Its tests assert the CLI's output and exit code, never the double's calls.

- [ ] **Step 5: Run the focused test and unit suite GREEN**

Run: `uv run pytest tests/unit/test_smoke.py::test_cli_prints_passing_json_report_from_lvim -v && make test-unit`

Expected: both commands pass.

- [ ] **Step 6: Commit the public CLI foundation**

```bash
git add script/smoke.py tests/unit/conftest.py tests/unit/test_smoke.py
git commit -m "feat(test): add smoke CLI foundation"
```

### Task 2: Lock down orchestrator policy with focused unit tests

**Files:**
- Modify: `tests/unit/test_smoke.py`
- Modify: `script/smoke.py`

**Interfaces:**
- Consumes: runner reports with `results[*].checks[*].status` and optional `runner_error`.
- Produces: `report_exit_code(report, mode) -> int`, `stage_fixtures()`, `build_lvim_command()`, and failure code `2` for invalid CLI/tool resolution.

- [ ] **Step 1: Write independent failing tests for staging and exit policy**

```python
def test_stage_fixtures_preserves_dotfiles(tmp_path: Path, smoke):
    source = tmp_path / "source"
    (source / "ssh" / ".ssh").mkdir(parents=True)
    (source / "ssh" / ".ssh" / "config").write_text("Host smoke\n")
    (source / "shell").mkdir()
    (source / "shell" / ".zshrc").write_text("setopt prompt_subst\n")
    staged = smoke.stage_fixtures(source, tmp_path / "stage")
    assert (staged / "ssh" / ".ssh" / "config").read_text() == "Host smoke\n"
    assert (staged / "shell" / ".zshrc").read_text() == "setopt prompt_subst\n"

def test_e2e_fails_missing_binary_skip_but_smoke_allows_it(smoke):
    report = {"results": [{"checks": [{
        "name": "lsp", "status": "skip",
        "message": "bash-language-server not installed",
    }]}]}
    assert smoke.report_exit_code(report, "smoke") == 0
    assert smoke.report_exit_code(report, "e2e") == 1
```

- [ ] **Step 2: Verify the tests are RED**

Run: `uv run pytest tests/unit/test_smoke.py::test_stage_fixtures_preserves_dotfiles tests/unit/test_smoke.py::test_e2e_fails_missing_binary_skip_but_smoke_allows_it -v`

Expected: each fails because dotfile copying and mode-specific skip classification are not implemented.

- [ ] **Step 3: Add the smallest pure helpers**

```python
def stage_fixtures(source: Path, staging_root: Path) -> Path:
    destination = staging_root / "fixtures"
    shutil.copytree(source, destination)
    return destination

def is_version_skip(message: str) -> bool:
    return message.startswith("nvim version ")

def report_exit_code(report: dict[str, object], mode: str) -> int:
    if report.get("runner_error"):
        return 1
    checks = [
        check for result in report.get("results", [])
        for check in result.get("checks", [])
    ]
    if any(check["status"] == "fail" for check in checks):
        return 1
    if mode == "e2e" and any(
        check["status"] == "skip" and not is_version_skip(check["message"])
        for check in checks
    ):
        return 1
    return 0
```

- [ ] **Step 4: Add RED/GREEN cycles for `--only`, timeout, missing report, and missing lvim**

```python
def test_command_passes_only_filter_to_runner(smoke, tmp_path: Path):
    command = smoke.build_lvim_command(
        tmp_path / "lvim", tmp_path / "runner.lua", tmp_path / "fixtures",
        tmp_path / "report.json", "shell/*",
    )
    assert any("SMOKE_ONLY='shell/*'" in argument for argument in command)

def test_timeout_returns_one(smoke, monkeypatch):
    def timeout(*_args, **_kwargs):
        raise subprocess.TimeoutExpired("lvim", 1)
    monkeypatch.setattr(smoke.subprocess, "run", timeout)
    assert smoke.main(["--timeout", "1"]) == 1

def test_missing_report_returns_one(smoke, tmp_path: Path):
    lvim = write_lvim_stub(tmp_path, {})
    assert smoke.main(["--lvim", str(lvim), "--json"]) == 1

def test_missing_lvim_returns_two(smoke, tmp_path: Path):
    assert smoke.main(["--lvim", str(tmp_path / "missing-lvim")]) == 2

def test_render_report_contains_fixture_and_check_status(smoke):
    console = Console(record=True, width=160)
    smoke.render_report(
        {"results": [{"path": "shell/script.sh", "ft_got": "sh", "checks": [
            {"name": "opens", "status": "pass", "message": ""},
        ]}]},
        console,
    )
    output = console.export_text()
    assert "shell/script.sh" in output
    assert "opens" in output
```

For each test: run its exact pytest node red; implement only its corresponding branch;
run the node green before writing the next test. `build_lvim_command()` must pass
`SMOKE_ROOT`, `SMOKE_OUT`, `SMOKE_MODE`, and `SMOKE_ONLY` as Lua globals, and
`runner_env()` must set `LUNARVIM_CONFIG_DIR` only when `--target` is supplied.

- [ ] **Step 5: Verify all fast orchestrator behavior**

Run: `make test-unit`

Expected: pass without Neovim or Docker.

- [ ] **Step 6: Commit the tested policy**

```bash
git add script/smoke.py tests/unit/conftest.py tests/unit/test_smoke.py
git commit -m "feat(test): add smoke report policy"
```

### Task 3: Add the committed fixture corpus and literal manifest contract

**Files:**
- Create: `tests/smoke/fixtures/README.md`
- Modify: `tests/smoke/fixtures/shell/script.sh`
- Create: `tests/smoke/fixtures/shell/.zshrc`
- Create: `tests/smoke/fixtures/yaml/config.yaml`
- Create: `tests/smoke/fixtures/yaml/playbooks/site.yml`
- Create: `tests/smoke/fixtures/yaml/deployment.yaml`
- Create: `tests/smoke/fixtures/ini/settings.ini`
- Create: `tests/smoke/fixtures/ini/foo.service`
- Create: `tests/smoke/fixtures/ssh/.ssh/config`
- Create: `tests/smoke/fixtures/log/app.log`
- Create: `tests/smoke/fixtures/text/notes.txt`
- Create: `tests/smoke/fixtures/json/data.json`
- Create: `tests/smoke/fixtures/json/package.json`
- Create: `tests/smoke/fixtures/json/tsconfig.json`
- Create: `tests/smoke/fixtures/xml/pom.xml`
- Create: `tests/smoke/fixtures/xml/Info.plist`
- Create: `tests/smoke/fixtures/python/main.py`
- Create: `tests/smoke/fixtures/python/test_sample.py`
- Create: `tests/smoke/fixtures/python/pyproject.toml`
- Create: `tests/smoke/fixtures/make/Makefile`
- Create: `tests/smoke/fixtures/just/justfile`
- Create: `tests/smoke/fixtures/just/.justfile`
- Create: `tests/smoke/fixtures/markdown/README.md`
- Create: `tests/smoke/fixtures/toml/Cargo.toml`
- Create: `tests/smoke/fixtures/git/.gitignore`
- Create: `tests/smoke/fixtures/lua/init.lua`
- Create: `tests/smoke/fixtures/docker/Dockerfile`
- Create: `tests/smoke/manifest.lua`
- Create: `tests/testinfra/test_e2e.py`
- Modify: `.gitignore`
- Modify: `.dockerignore`
- Modify: `tests/unit/test_smoke.py`

**Interfaces:**
- Produces: a fixture root that staging preserves byte-for-byte and a Lua table consumed only by `runner.lua`.
- Consumes: current `config.lua` filetype rules, treesitter parser list, LSP configurations, and format-on-save patterns.

- [ ] **Step 1: Add the minimal log fixture, then write failing tracking and Docker-context contracts**

Create `tests/smoke/fixtures/log/app.log` with these three lines before the tests:

```text
2026-08-21T12:00:00Z INFO smoke runner started
2026-08-21T12:00:01Z WARN fixture warning
2026-08-21T12:00:02Z ERROR fixture failure
```

```python
def test_repository_fixture_files_are_not_ignored():
    fixtures = [
        "tests/smoke/fixtures/log/app.log",
        "tests/smoke/fixtures/ini/settings.ini",
        "tests/smoke/fixtures/shell/.zshrc",
        "tests/smoke/fixtures/git/.gitignore",
        "tests/smoke/fixtures/just/.justfile",
    ]
    result = subprocess.run(
        ["git", "check-ignore", "-q", *fixtures],
        cwd=REPO_ROOT, check=False,
    )
    assert result.returncode == 1
```

- [ ] Add a real Docker build-context assertion:

```python
def test_smoke_assets_exist_in_image(host):
    assert host.file(
        "/root/lunarvim-config/tests/smoke/fixtures/log/app.log"
    ).exists
```

- [ ] **Step 2: Verify RED**

Run:

```bash
uv run pytest tests/unit/test_smoke.py::test_repository_fixture_files_are_not_ignored -v
make docker-build
uv run pytest tests/testinfra/test_e2e.py::test_smoke_assets_exist_in_image -v
```

Expected: the unit test fails because `.gitignore` matches
`tests/smoke/fixtures/log/app.log`; the Docker assertion fails because `.dockerignore`
excludes the `tests/` directory from the image.

- [ ] **Step 3: Add fixture contents, manifest expectations, and ignore exceptions**

Add `.gitignore` negations:

```gitignore
!tests/smoke/
!tests/smoke/fixtures/
!tests/smoke/fixtures/log/
!tests/smoke/fixtures/log/*.log
```

Remove the `tests` line from `.dockerignore` so Docker receives the fixture corpus and
runner. Write `tests/smoke/fixtures/README.md` with the exact instruction:
“These files are opened by `make smoke`. Add a fixture and literal manifest expectation
whenever a filetype or runtime regression is discovered.”

Create small, realistic files matching the exact names above. Preserve these literal
manifest expectations:

```lua
return {
  { path = "shell/script.sh", ft = "sh", parser = "bash", lsp = { "bashls" }, format = "shfmt" },
  { path = "shell/.zshrc", ft = "zsh", parser = "bash", lsp = { "bashls" } },
  { path = "yaml/config.yaml", ft = "yaml", parser = "yaml", lsp = { "yamlls" } },
  { path = "yaml/playbooks/site.yml", ft = "yaml.ansible", parser = "yaml", lsp = { "ansiblels" } },
  { path = "yaml/deployment.yaml", ft = "yaml", parser = "yaml", lsp = { "yamlls" } },
  { path = "ini/settings.ini", ft = "dosini", parser = "ini" },
  { path = "ini/foo.service", ft = "systemd", parser = "ini" },
  { path = "ssh/.ssh/config", ft = "sshconfig", syntax = true },
  { path = "log/app.log", ft = "log", syntax = true },
  { path = "text/notes.txt", ft = "text", syntax = true, lsp = { "vale_ls" } },
  { path = "json/data.json", ft = "json", parser = "json", lsp = { "jsonls" }, format = "jsonls" },
  { path = "json/package.json", ft = "json", parser = "json", lsp = { "jsonls" }, format = "jsonls" },
  { path = "json/tsconfig.json", ft = "jsonc", parser = "jsonc", lsp = { "jsonls" }, format = "jsonls" },
  { path = "xml/pom.xml", ft = "xml", syntax = true },
  { path = "xml/Info.plist", ft = "xml", syntax = true },
  { path = "python/main.py", ft = "python", parser = "python", lsp = { "basedpyright", "ruff" }, format = "ruff" },
  { path = "python/test_sample.py", ft = "python", parser = "python", lsp = { "basedpyright", "ruff" }, format = "ruff" },
  { path = "make/Makefile", ft = "make", parser = "make" },
  { path = "just/justfile", ft = "just", syntax = true, min_nvim = "0.10" },
  { path = "just/.justfile", ft = "just", syntax = true, min_nvim = "0.10" },
  { path = "markdown/README.md", ft = "markdown", parser = "markdown" },
  { path = "toml/Cargo.toml", ft = "toml", parser = "toml", lsp = { "taplo" } },
  { path = "git/.gitignore", ft = "gitignore", parser = "gitignore" },
  { path = "lua/init.lua", ft = "lua", parser = "lua", format = "stylua" },
  { path = "docker/Dockerfile", ft = "dockerfile", parser = "dockerfile", lsp = { "dockerls" } },
}
```

- [ ] **Step 4: Run the fixture contract GREEN**

Run:

```bash
uv run pytest tests/unit/test_smoke.py::test_repository_fixture_files_are_not_ignored tests/unit/test_smoke.py::test_stage_fixtures_preserves_dotfiles -v
make docker-build
uv run pytest tests/testinfra/test_e2e.py::test_smoke_assets_exist_in_image -v
```

Expected: all commands pass; `git check-ignore` exits `1` because none of the fixtures
are ignored, and the image contains the fixture corpus.

- [ ] **Step 5: Commit the corpus**

```bash
git add .gitignore .dockerignore tests/smoke/fixtures tests/smoke/manifest.lua tests/unit/test_smoke.py tests/testinfra/test_e2e.py
git commit -m "test: add LunarVim smoke fixtures"
```

### Task 4: Prove a minimal runner checks real file opening

**Files:**
- Create: `tests/smoke/runner.lua`
- Modify: `tests/testinfra/test_e2e.py`
- Modify: `script/smoke.py`

**Interfaces:**
- Consumes: `SMOKE_ROOT`, `SMOKE_OUT`, `SMOKE_MODE`, `SMOKE_ONLY`, and `manifest.lua`.
- Produces: one report result per selected fixture and check-level `{ name, status, message }` records.

- [ ] **Step 1: Write the failing real-image `opens` contract**

```python
def test_e2e_shell_fixture_opens_and_reports_filetype(host):
    result = host.run(
        "cd /root/lunarvim-config && "
        "uv run script/smoke.py --mode e2e --only 'shell/script.sh' --json"
    )
    report = json.loads(result.stdout)
    fixture = report["results"][0]
    assert result.rc == 0, result.stderr
    assert fixture["path"] == "shell/script.sh"
    assert fixture["ft_got"] == "sh"
    assert {check["name"] for check in fixture["checks"]} >= {"opens", "filetype"}
```

- [ ] **Step 2: Verify RED against the Docker image**

Run: `uv run pytest tests/testinfra/test_e2e.py::test_e2e_shell_fixture_opens_and_reports_filetype -v`

Expected: fail because `runner.lua` does not yet write the report.

- [ ] **Step 3: Implement compatible runner bootstrap and `opens`/`filetype`**

```lua
vim.o.lines = 50
vim.o.columns = 160
vim.o.more = false
vim.o.swapfile = false
vim.o.confirm = false

local function check(name, status, message)
  return { name = name, status = status, message = message or "" }
end

local function run_fixture(entry)
  local path = SMOKE_ROOT .. "/" .. entry.path
  local checks = {}
  vim.v.errmsg = ""
  local opened, err = pcall(vim.cmd.edit, vim.fn.fnameescape(path))
  table.insert(checks, check("opens", opened and vim.v.errmsg == "" and "pass" or "fail", err or vim.v.errmsg))
  table.insert(checks, check("filetype", vim.bo.filetype == entry.ft and "pass" or "fail",
    string.format("expected %s, got %s", entry.ft, vim.bo.filetype)))
  return { path = entry.path, ft_got = vim.bo.filetype, checks = checks }
end
```

Use `vim.fn.json_encode()` and `io.open(SMOKE_OUT, "w")` to write the report. Wrap
the complete run in `xpcall()` and emit `{ runner_error = tostring(err), results = {} }`
on an unexpected error. Filter `entry.path` with `vim.fn.match()` when `SMOKE_ONLY` is
non-empty.

- [ ] **Step 4: Verify GREEN**

Run: `uv run pytest tests/testinfra/test_e2e.py::test_e2e_shell_fixture_opens_and_reports_filetype -v`

Expected: pass using the actual Docker LunarVim runtime.

- [ ] **Step 5: Commit the observable runner core**

```bash
git add script/smoke.py tests/smoke/runner.lua tests/testinfra/test_e2e.py
git commit -m "feat(test): open smoke fixtures headlessly"
```

### Task 5: Expand runner checks in separate red-green slices

**Files:**
- Modify: `tests/smoke/runner.lua`
- Modify: `tests/testinfra/test_e2e.py`
- Modify: `tests/unit/test_smoke.py`

**Interfaces:**
- Produces: `highlight`, `lsp`, `lsp_healthy`, `edit`, and `format` records alongside `opens` and `filetype`.
- Consumes: `manifest.lua` parser/syntax, LSP, formatter, and version-bound fields.

- [ ] **Step 1: Add a failing parser and syntax assertion**

```python
def test_e2e_reports_treesitter_and_builtin_syntax(host):
    result = host.run(
        "cd /root/lunarvim-config && "
        "uv run script/smoke.py --mode e2e --only 'xml/Info.plist' --json"
    )
    report = json.loads(result.stdout)
    checks = {c["name"]: c for c in report["results"][0]["checks"]}
    assert result.rc == 0, result.stderr
    assert checks["highlight"]["status"] == "pass"
```

- [ ] **Step 2: Verify RED, then implement the compatibility-safe highlight helper**

Run: `uv run pytest tests/testinfra/test_e2e.py::test_e2e_reports_treesitter_and_builtin_syntax -v`

Expected: fail because `highlight` is absent.

```lua
local function has_active_highlighter(bufnr)
  local ok, highlighter = pcall(require, "vim.treesitter.highlighter")
  return ok and highlighter.active[bufnr] ~= nil
end

local function highlight_check(entry, bufnr)
  if entry.parser then
    local has_parser = require("nvim-treesitter.parsers").has_parser(entry.parser)
    local active = vim.wait(1000, function() return has_active_highlighter(bufnr) end, 25)
    return check("highlight", has_parser and active and "pass" or "fail",
      string.format("parser=%s highlighter=%s", tostring(has_parser), tostring(active)))
  end
  local active = vim.wait(500, function() return vim.b[bufnr].current_syntax ~= nil end, 25)
  return check("highlight", active and "pass" or "fail", "builtin syntax=" .. tostring(vim.b[bufnr].current_syntax))
end
```

- [ ] **Step 3: Add a failing LSP policy test, then implement client compatibility**

```python
def test_e2e_shell_fixture_attaches_and_keeps_lsp_healthy(host):
    result = host.run(
        "cd /root/lunarvim-config && "
        "uv run script/smoke.py --mode e2e --only 'shell/script.sh' --json"
    )
    report = json.loads(result.stdout)
    checks = {check["name"]: check for check in report["results"][0]["checks"]}
    assert result.rc == 0, result.stderr
    assert checks["lsp"]["status"] == "pass"
    assert checks["lsp_healthy"]["status"] == "pass"
```

Run: `uv run pytest tests/testinfra/test_e2e.py::test_e2e_shell_fixture_attaches_and_keeps_lsp_healthy -v`

Expected: fail because the runner has no LSP check.

Implement:

```lua
local function clients_for(bufnr)
  if vim.lsp.get_clients then
    return vim.lsp.get_clients { bufnr = bufnr }
  end
  return vim.lsp.get_active_clients { bufnr = bufnr }
end

local lsp_bins = {
  ansiblels = "ansible-language-server", bashls = "bash-language-server",
  basedpyright = "basedpyright-langserver", dockerls = "docker-langserver",
  jsonls = "vscode-json-language-server", ruff = "ruff", taplo = "taplo",
  vale_ls = "vale-ls", yamlls = "yaml-language-server",
}
```

For each expected server, classify `vim.fn.executable(lsp_bins[name]) == 0` as
`skip` in smoke and `fail` in e2e. Wait up to 5000 milliseconds for executable
servers to attach; report missing client names. Mark `lsp_healthy` failed for stopped
clients or new messages matching `server exited`, `rpc`, or `Client %d+ quit`.

- [ ] **Step 4: Add failing edit and format tests, then implement only their checks**

```python
def test_e2e_shell_fixture_runs_edit_and_format_checks(host):
    result = host.run(
        "cd /root/lunarvim-config && "
        "uv run script/smoke.py --mode e2e --only 'shell/script.sh' --json"
    )
    report = json.loads(result.stdout)
    checks = {check["name"]: check for check in report["results"][0]["checks"]}
    assert result.rc == 0, result.stderr
    assert checks["edit"]["status"] == "pass"
    assert checks["format"]["status"] == "pass"

def test_e2e_lua_fixture_runs_edit_and_format_checks(host):
    result = host.run(
        "cd /root/lunarvim-config && "
        "uv run script/smoke.py --mode e2e --only 'lua/init.lua' --json"
    )
    report = json.loads(result.stdout)
    checks = {check["name"]: check for check in report["results"][0]["checks"]}
    assert result.rc == 0, result.stderr
    assert checks["edit"]["status"] == "pass"
    assert checks["format"]["status"] == "pass"
```

Run each node red before adding its code. The runner must insert and undo `smoke`,
call `startinsert()`/`stopinsert()`, then snapshot new messages. It must write only
the staged buffer, call synchronous `vim.lsp.buf.format({ async = false, timeout_ms = 5000,
bufnr = bufnr })`, and compare to `<fixture>.formatted` only if that sibling exists.

- [ ] **Step 5: Verify runner slices GREEN**

Run: `uv run pytest tests/testinfra/test_e2e.py -v && make test-unit`

Expected: the selected e2e contracts and fast unit tests pass; known baseline fixtures
are tested separately in Task 7 and are not hidden by these focused passing cases.

- [ ] **Step 6: Commit expanded checks**

```bash
git add tests/smoke/runner.lua tests/testinfra/test_e2e.py tests/unit/test_smoke.py
git commit -m "feat(test): validate smoke runtime checks"
```

### Task 6: Make strict Docker provisioning match the manifest

**Files:**
- Modify: `Dockerfile`
- Modify: `tests/testinfra/test_binaries.py`
- Modify: `Makefile`

**Interfaces:**
- Produces: `make e2e`, which runs `uv run script/smoke.py --mode e2e` inside `lunarvim-config:test`.
- Consumes: all in-range manifest LSP names and treesitter parsers.

- [ ] **Step 1: Write failing package/parser assertions**

```python
@pytest.mark.parametrize("package", [
    "ansible-language-server", "bash-language-server", "dockerfile-language-server",
    "json-lsp", "taplo", "yaml-language-server",
])
def test_manifest_lsp_package_installed(host, mason_packages, package):
    assert host.file(f"{mason_packages}/{package}").exists

@pytest.mark.parametrize("parser", ["bash", "python", "lua", "json", "jsonc", "yaml",
                                    "toml", "ini", "dockerfile", "make", "markdown",
                                    "markdown_inline", "gitignore"])
def test_manifest_parser_installed(run_lua, parser):
    result = run_lua(
        "local p=require('nvim-treesitter.parsers'); "
        f"io.write('<<HAS='..tostring(p.has_parser('{parser}'))..'>>')"
    )
    assert "<<HAS=true>>" in result.stdout + result.stderr
```

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/testinfra/test_binaries.py -v`

Expected: fail for newly required Ansible package and any missing parser before Dockerfile changes.

- [ ] **Step 3: Provision the exact strict-runtime dependencies**

Update the Docker `MasonInstall` command to include `ansible-language-server`. Update
`TSInstallSync` to include `make markdown markdown_inline gitignore git_config` in
addition to the existing parser list. Do not include XML or `ssh_config`, which are
intentionally builtin-syntax fallbacks on the 0.9 pin.

Add:

```make
e2e: docker-build ## Strict smoke e2e test inside the pinned Docker image
	docker run --rm lunarvim-config:test uv run script/smoke.py --mode e2e $(ARGS)
```

Add `e2e` to `.PHONY`, but do not add it to `test-all` while the intentional baseline
is red. The later green follow-up adds it to `test-all` without an allow-failure flag.

- [ ] **Step 4: Verify GREEN**

Run: `uv run pytest tests/testinfra/test_binaries.py -v`

Expected: all manifest-provisioning assertions pass.

- [ ] **Step 5: Commit strict runtime provisioning**

```bash
git add Dockerfile Makefile tests/testinfra/test_binaries.py
git commit -m "test: provision strict smoke runtime"
```

### Task 7: Capture the known red baseline and document the feedback loop

**Files:**
- Modify: `tests/testinfra/test_e2e.py`
- Modify: `Makefile`
- Modify: `CLAUDE.md`
- Modify: `specs/install.md`

**Interfaces:**
- Produces: `make smoke`, `make deploy-smoke`, and a machine-readable baseline report.
- Consumes: the real deployed local configuration for `smoke` and the Docker image for `e2e`.

- [ ] **Step 1: Write a baseline-detection test before accepting the current regression**

```python
def test_e2e_log_fixture_reports_current_filetype_regression(host):
    result = host.run(
        "cd /root/lunarvim-config && "
        "uv run script/smoke.py --mode e2e --only 'log/app.log' --json"
    )
    report = json.loads(result.stdout)
    checks = {c["name"]: c for c in report["results"][0]["checks"]}
    assert result.rc == 1
    assert checks["filetype"]["status"] == "fail"
    assert "expected log" in checks["filetype"]["message"]
```

- [ ] **Step 2: Verify RED before runner filetype implementation, then GREEN as a detection test**

Run: `uv run pytest tests/testinfra/test_e2e.py::test_e2e_log_fixture_reports_current_filetype_regression -v`

Expected before the filetype check exists: fail because no `filetype` result is emitted.
Expected after Task 4's implementation: pass because the real known regression is
reported as a failure. This is baseline evidence, not a passing e2e suite.

- [ ] **Step 3: Add local Make targets and documentation**

```make
smoke: ## Smoke-test the deployed config with the active local LunarVim
	@uv run script/smoke.py --mode smoke $(ARGS)

deploy-smoke: deploy smoke ## Deploy and smoke-test the active system
```

Add to `CLAUDE.md` Testing:

```text
make smoke          # active-system post-deploy smoke suite; missing local tools are reported as skips
make deploy-smoke   # deploy then run the active-system smoke suite
make e2e            # strict Docker smoke suite for Neovim 0.9.5
```

Document that post-deploy changes to `config.lua`, `ftplugin/`, `ftdetect/`, `after/`,
or `lsp-settings/` require `make deploy-smoke`, and regressions must first receive a
fixture/manifest assertion run red. Document the `lines`/`columns` headless mitigation
and the requirement to write reports to a file rather than `io.write`.

Append to the deploy usage in `specs/install.md`:

```text
After a successful deploy, run `make smoke` to open the committed fixture corpus with
the active LunarVim runtime.
```

- [ ] **Step 4: Verify the baseline and all non-baseline tests**

Run: `make smoke ARGS="--only 'log/app.log' --json"; make test-unit; uv run pytest tests/testinfra/test_e2e.py -v`

Expected: the focused local/Docker baseline reports `log` as a real failure; Python
tests pass because the baseline test asserts detection. Do not run `make e2e` as a
passing gate while the baseline is intentionally red.

- [ ] **Step 5: Commit the user-facing feedback loop**

```bash
git add Makefile CLAUDE.md specs/install.md tests/testinfra/test_e2e.py
git commit -m "docs(test): document LunarVim smoke feedback loop"
```

## Explicitly Excluded Green Follow-up

The approved specification keeps config repairs out of this smoke-suite implementation.
The subsequent, separately approved work starts from the Task 7 red reports, applies
active `config.lua` detection rules for `.log`, `justfile`, and `.justfile`, updates
none-ls only after choosing a verified 0.9.5-and-0.11-compatible revision, and changes
the baseline detector into a full `make e2e` zero-exit test. Only that green follow-up
modifies `.github/workflows/ci.yml` to run strict e2e without `continue-on-error`.

## Plan Self-Review

**Spec coverage:** Tasks 1-2 implement the Python CLI, environment, staging, report,
display, and exit policy. Task 3 supplies the full required corpus, manifest, and
tracking/build-context fixes. Tasks 4-5 implement every runner check and the Neovim
0.9/0.11 API boundary. Task 6 provisions strict Docker runtime requirements and Make
integration. Task 7 retains and documents the intentional red baseline. The separately
approved green follow-up turns that baseline green, then adds `e2e` to `test-all` and
the blocking CI step only after `make e2e` is real-green.

**Placeholder scan:** No task relies on source-text assertions, mock-interaction
assertions, an unspecified dependency, or an unbounded "add tests" instruction.

**Type consistency:** Python's `main`, `stage_fixtures`, `build_lvim_command`,
`runner_env`, `load_report`, `render_report`, and `report_exit_code` are defined once
and consumed consistently.
Lua's manifest and report schema are defined before runner and testinfra tasks use them.
