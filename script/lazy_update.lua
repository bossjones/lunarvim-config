-- Drive a Lazy update and report the result. Used by `make plugins-update` (with
-- $LVIM_DEV_MODE set) and `make plugins-restore` (without it).
--
-- LunarVim stamps a pinned SHA from lvim/snapshots/default.json onto every core plugin
-- spec (lvim/lua/lvim/plugins.lua), and lazy's Git.get_target() honors `plugin.commit`
-- ahead of any branch or tag. $LVIM_DEV_MODE is LunarVim's own switch for skipping that
-- stamping, so it is the difference between the two modes:
--
--   LVIM_DEV_MODE=1  -> snapshot pins skipped; every plugin moves to its branch/tag tip.
--   (unset)          -> snapshot pins applied; every plugin returns to LunarVim's pin.
--
-- `commit` pins written in config.lua are ours and win in BOTH modes, because config.lua's
-- specs are merged after lvim/plugins.lua and lazy's Spec:merge does
-- `setmetatable(new, { __index = old })`.
--
-- Dirty checkouts are never clobbered: lazy's `git.status` task runs `git ls-files -d -m`
-- and sets task.error on local changes, and the runner then aborts that plugin's pipeline
-- before `git.checkout` runs. Headless with show=false that would be silent, so every
-- errored task is reported and the process exits non-zero.

local ok, manage = pcall(require, "lazy.manage")
if not ok then
  io.stderr:write "lazy_update.lua: lazy.nvim is not available. Launch `lvim` once first.\n"
  vim.cmd "cquit 1"
  return
end

if vim.env.LVIM_DEV_MODE then
  print "mode: UPDATE (LVIM_DEV_MODE set - LunarVim's snapshot pins are skipped)"
else
  print "mode: RESTORE (LunarVim's snapshot pins are applied)"
end

manage.update { wait = true, show = false }

-- Rewrite lazy-lock.json from what is actually on disk. manage.update() registers its own
-- lock callback on an already-drained runner, so calling this directly is what guarantees
-- the lockfile is current before we quit.
require("lazy.manage.lock").update()

local plugins = require("lazy.core.config").plugins

local names = {}
for name, _ in pairs(plugins) do
  table.insert(names, name)
end
table.sort(names)

local moved, failed = 0, 0

for _, name in ipairs(names) do
  local plugin = plugins[name]

  for _, task in ipairs(plugin._ and plugin._.tasks or {}) do
    if task.error then
      failed = failed + 1
      io.stderr:write(("SKIPPED %s (%s): %s\n"):format(name, task.name, vim.trim(task.error)))
    end
  end

  local up = plugin._ and plugin._.updated
  if up and up.from ~= up.to then
    moved = moved + 1
    print(("moved %s: %s -> %s"):format(name, up.from:sub(1, 7), up.to:sub(1, 7)))
  end
end

print(("\n%d plugin(s) moved, %d skipped, %d total."):format(moved, failed, #names))

if failed > 0 then
  io.stderr:write(("\n%d plugin(s) were NOT touched (see SKIPPED above). Nothing was overwritten.\n"):format(failed))
  io.stderr:write "Resolve the local changes in those checkouts, then re-run.\n"
  vim.cmd "cquit 1"
end
