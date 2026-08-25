# `script/install.py` — LunarVim config installer

A single, testable Python entry point (run via `uv run`) that safely deploys this repo's
LunarVim configuration to `~/.config/lvim/`. It **backs up** any existing config (zip
snapshot), **moves it aside** to a timestamped directory so the target starts clean, then
**installs** the config payload. Supports a `--dry-run` preview and renders colored,
syntax-highlighted diffs of changed files with [`rich`](https://github.com/Textualize/rich).

It supersedes the hand-maintained `make backup` + `make sync` shell targets
(`Makefile:7-34`) with one source of truth for the deploy manifest and a preview of exactly
what will change.

## Usage

```bash
# Preview what would happen — changes nothing on disk
uv run script/install.py --dry-run

# Install (prompts for confirmation before touching anything)
uv run script/install.py

# Install without the interactive prompt
uv run script/install.py --yes

# Install into an alternate target (useful for testing)
uv run script/install.py --yes --target /tmp/lvim-test --repo .

# Via Makefile
make deploy                    # interactive install
make deploy ARGS=--dry-run     # preview
```

## Flags

| Flag | Default | Purpose |
| ------ | --------- | --------- |
| `--dry-run` | off | Print the plan + diffs and exit without modifying the filesystem. |
| `-y`, `--yes` | off | Skip the interactive confirmation prompt. |
| `--target DIR` | `~/.config/lvim` | Destination directory for the config. |
| `--repo DIR` | script's repo root | Source directory to install *from*. |
| `--no-backup` | off | Skip the zip snapshot **and** the move-aside; overwrite in place. |

## What gets installed (manifest)

The installer deploys exactly these 16 items (single source of truth: the `MANIFEST`
constant in `script/install.py`). This matches `make sync` **minus `.git`**, which is
intentionally excluded — a deployed config should not carry the repo's git directory, and
the backup already excludes it.

**Files:** `Makefile`, `config.lua`, `README.md`, `.luarc.json`, `.luacheckrc`,
`.markdownlint.json`, `.stylua.toml`, `.gitignore`, `LICENSE`

**Directories:** `lsp-settings/`, `ftplugin/`, `after/`, `.vale/`, `ftdetect/`,
`snippets/`, `lua/`

Anything else in the repo root (tooling/meta such as `pyproject.toml`, `bootstrap.sh`,
`Dockerfile`, `tests/`, `specs/`, `script/`, `.github/`, `.git/`) is **not** deployed.

## Backup & move-aside semantics

Before installing (unless `--no-backup`), if the target directory exists:

1. **Zip snapshot** → `~/.config/lvim-backups/lvim-backup-<timestamp>.zip`, excluding
   `.git/` (mirrors the existing `make backup` exclusion).
2. **Move aside** → the existing `~/.config/lvim` is renamed to
   `~/.config/lvim.bak.<timestamp>`, leaving the target path clean for a fresh install.

`<timestamp>` is `YYYYmmdd-HHMMSS`. If the target does not exist (fresh machine), backup is
a no-op and the installer proceeds straight to install.

The scope is `~/.config/lvim` **only** — Neovim's own `~/.config/nvim` and runtime data
dirs (`~/.local/share/lunarvim`, `~/.local/share/nvim`) are left untouched.

## Diff behavior

For each file in the plan the installer classifies the action:

- **CREATE** — file does not exist at the target.
- **OVERWRITE** — file exists but differs; a unified diff (`difflib.unified_diff`) is
  computed and rendered with `rich.syntax.Syntax(..., "diff")` for color highlighting.
- **UNCHANGED** — byte-identical; no diff.

Binary files are detected (NUL-byte heuristic) and marked without attempting a text diff.

## Exit codes

| Code | Meaning |
| ------ | --------- |
| `0` | Success (install completed, or `--dry-run` preview rendered). |
| `1` | Runtime error (e.g. source repo missing manifest items, copy failure). |
| `2` | Bad arguments (argparse usage error, or `--repo` path does not exist). |

## Design notes

- Follows the conventions of `script/doctor.py`: PEP 723 inline metadata
  (`dependencies = ["rich>=13.0"]`, `requires-python = ">=3.10"`),
  `from __future__ import annotations`, `@dataclass`/`Enum` models, `rich`
  `Console`/`Table`/`Panel`, `main() -> int` + `sys.exit(main())`.
- Core logic is pure and parameterized (`repo`, `target`, `backups_dir`, injected
  `timestamp`) so it is unit-tested against `tmp_path` and never touches the real `$HOME`.
- Cross-platform (macOS + Linux): stdlib `pathlib` / `shutil` / `zipfile` / `difflib`
  only; `rich` is the sole third-party dependency, supplied per-script by `uv run`.

## Test matrix

Fast unit tests (no Docker) live in `tests/unit/test_install.py`, run via
`uv run pytest tests/unit -v` (or `make test-unit`):

| Test | Asserts |
| ------ | --------- |
| `test_manifest_excludes_git_and_repo_meta` | `MANIFEST` = the 16 items; no `.git`, `pyproject.toml`, `tests`, `specs`, `bootstrap.sh`. |
| `test_build_plan_all_create_on_empty_target` | Empty target → every action is `CREATE`. |
| `test_build_plan_unchanged_for_identical_file` | Identical content → `UNCHANGED`, empty diff. |
| `test_build_plan_overwrite_has_unified_diff` | Changed text file → `OVERWRITE`, diff contains `---`/`+++`/`@@`. |
| `test_binary_file_marked_no_diff` | Binary content → `is_binary=True`, no diff. |
| `test_backup_creates_zip` | Existing target → zip at `backups_dir/lvim-backup-<ts>.zip`, excludes `.git`. |
| `test_backup_moves_target_aside` | Existing target moved to `<name>.bak.<ts>`; original path gone. |
| `test_backup_noop_when_target_missing` | Missing target → no zip, no error, returns `None`s. |
| `test_dry_run_makes_no_filesystem_changes` | Dry-run leaves target + backups_dir untouched. |
| `test_apply_copies_every_manifest_item` | After apply, each present manifest item is byte-identical at target. |
| `test_git_not_deployed` | A `.git/` in the source repo is absent from the target after apply. |
| `test_exit_code_zero_on_success` / `test_exit_code_two_on_bad_target` | `main([...])` return codes. |
