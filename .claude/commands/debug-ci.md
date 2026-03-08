---
description: Debug failed GitHub Actions CI runs — diagnose, fix, validate locally, commit, push, and poll until the new run passes. Supports up to 3 retry cycles.
allowed-tools: [Bash, Read, Edit, Write, Glob, Grep, Agent]
---

# Debug CI Command

You are a CI debugging assistant for this LunarVim config repository. Your job is to diagnose failed GitHub Actions CI runs, fix the issues, validate locally, push, and verify the new run passes. You operate in a 6-phase feedback loop with up to 3 outer retry cycles.

## Guardrails — READ FIRST

- **Max 3 outer cycles** (diagnose → fix → push → verify). If still failing after 3, report remaining failures and suggest manual investigation.
- **Max 3 inner iterations** per local validation phase.
- **Max 60 seconds** waiting for a new CI run to appear after push.
- **Max 10 minutes** polling a single CI run.
- **NEVER check the old failed run** — always find the new run by matching commit SHA.
- **NEVER use `git add -A` or `git add .`** — always stage specific files by name.
- **Always validate locally before pushing.**
- **Always use conventional commit prefixes**: `fix:` for lint fixes, `style:` for formatting, `ci:` for workflow changes, `docs:` for README/markdown.

## Phase 1: Diagnose

First, check if `gh` CLI is authenticated:

```bash
gh auth status
```

If not authenticated, tell the user to run `gh auth login` and stop.

Find recent CI runs on the current branch:

```bash
gh run list --branch $(git branch --show-current) --limit 5 --json status,conclusion,databaseId,createdAt,headSha
```

If an argument was provided to this command, use it as the run ID. Otherwise, pick the most recent failed run from the list.

**If no failed runs exist**: Report "All CI runs are green — nothing to fix!" and stop.

Get the failure details:

```bash
gh run view <run_id> --log-failed
```

Categorize the failure into one or more of:
- **luacheck** — Lua lint errors (undefined globals, unused variables, etc.)
- **stylua** — Lua formatting drift
- **shellcheck** — Shell script issues in `bootstrap.sh`
- **markdownlint** — Markdown formatting issues in `README.md`
- **lvim-headless** — Config load errors (Lua runtime errors)

Extract specific file paths and line numbers from the error output.

## Phase 2: Plan Fix

For each failure type, determine the fix strategy:

| Failure | Strategy |
|---------|----------|
| luacheck: undefined global | Add to `.luacheckrc` globals or fix the code |
| luacheck: unused variable | Prefix with `_` or remove if truly unused |
| luacheck: other | Read the specific file, understand context, apply fix |
| stylua | Run `stylua .` to auto-format all Lua files |
| shellcheck | Read `bootstrap.sh`, apply shellcheck-suggested fixes |
| markdownlint | Read `README.md`, fix formatting issues per markdownlint rules |
| lvim-headless | Read `config.lua` and related modules, debug Lua errors |

If multiple failure types exist in the same run, plan to fix ALL of them before pushing.

Read each failing file to understand context before making changes.

## Phase 3: Implement Fix

Apply targeted edits using the Edit tool. Be precise — only change what's needed to fix the CI failure.

Special cases:
- **stylua**: Just run `stylua .` via Bash — it auto-formats everything.
- **luacheck globals**: Check `.luacheckrc` first. If the global is legitimate (like `lvim`, `vim`, or a plugin global), add it there. Otherwise fix the code.
- **shellcheck**: Follow the SC#### code suggestions. Common fixes: quote variables, use `[[ ]]` instead of `[ ]`, etc.
- **markdownlint**: Follow the MD### rule. Common fixes: consistent heading levels, trailing whitespace, line length, etc.

## Phase 4: Local Validation

Run the same checks that CI runs, in a loop (max 3 iterations):

```bash
# Check if tools are available, skip with warning if not
command -v luacheck && luacheck . --globals lvim vim || echo "WARN: luacheck not installed, skipping local check"
command -v stylua && stylua --check . || echo "WARN: stylua not installed, skipping local check"
command -v shellcheck && shellcheck bootstrap.sh || echo "WARN: shellcheck not installed, skipping local check"
command -v markdownlint && markdownlint README.md || echo "WARN: markdownlint not installed, skipping local check"
```

Run each check **individually** so you can see which ones fail. If any check fails:
1. Read the error output
2. Apply the fix
3. Re-run the failing check
4. Repeat up to 3 times

Only proceed to Phase 5 when all available local checks pass (or tools are not installed).

## Phase 5: Commit & Push

Stage only the specific files you changed:

```bash
git add <file1> <file2> ...
```

Create a commit with the appropriate conventional commit prefix. Use a HEREDOC for the message:

```bash
git commit -m "$(cat <<'EOF'
<prefix>: <concise description of what was fixed>

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

Push and record the SHA:

```bash
git push
PUSH_SHA=$(git rev-parse HEAD)
echo "Pushed commit: $PUSH_SHA"
```

## Phase 6: Remote Validation (Smart Polling)

**CRITICAL**: You must verify the NEW run triggered by your push, not the old failed run.

### Step 1: Initial wait

Wait 15 seconds for GitHub to register the push and create a new workflow run.

```bash
sleep 15
```

### Step 2: Find the new run by commit SHA

```bash
gh run list --branch $(git branch --show-current) --limit 5 --json databaseId,headSha,status,conclusion,createdAt
```

Filter the results for a run where `headSha` matches `$PUSH_SHA`. If not found, retry every 15 seconds up to 4 times (60 seconds total). If still not found after 60 seconds, warn the user and provide the `gh run list` command to check manually.

### Step 3: Poll until complete

Once you have the new run ID:

```bash
gh run view <new_run_id> --json status,conclusion
```

Poll every 30 seconds until `status` is `completed`. Maximum 10 minutes of polling (20 iterations).

### Step 4: Evaluate result

- **Success** (`conclusion == "success"`):
  Report victory! Show the run URL:
  ```bash
  gh run view <new_run_id> --web
  ```
  Print a summary of what was fixed and stop.

- **Failure** (`conclusion == "failure"`):
  If this is outer cycle 1 or 2, loop back to Phase 1 using the new failed run ID.
  If this is outer cycle 3, report the remaining failures and suggest manual investigation.

- **Cancelled/other**:
  Report the status and suggest the user investigate manually.

## Output Format

At each phase, provide a brief status update:

```
## Cycle N/3

### Phase 1: Diagnose
Found failed run #<id> (<timestamp>)
Failures: luacheck (3 errors), stylua (formatting drift)

### Phase 2: Plan
- Fix 3 luacheck warnings in lua/user/plugins.lua
- Run stylua to auto-format

### Phase 3: Fix
- Fixed unused variable on line 42 of lua/user/plugins.lua
- Ran stylua .

### Phase 4: Local Validation
✓ luacheck passed
✓ stylua --check passed
✓ shellcheck passed (bootstrap.sh)

### Phase 5: Push
Committed: style: fix luacheck warnings and stylua formatting
Pushed: abc1234

### Phase 6: Verify
Waiting for new run...
Found run #<new_id> (in_progress)
Polling... (1/20)
...
✓ CI passed! https://github.com/.../actions/runs/<new_id>
```
