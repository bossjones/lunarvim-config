# AI completion — TabNine rollout (future)

Status: **planned, not implemented.** This spec documents how to reintroduce
AI completion (TabNine) into this LunarVim config later, deliberately and
reversibly. The active `config.lua` ships with **no** AI completion today.

## Goal

Add TabNine suggestions to LunarVim's bundled `nvim-cmp` completion menu so they
_augment_ (not override) the existing LSP + LuaSnip sources, while keeping the
lean core config untouched until the feature is intentionally switched on.

## Why TabNine (and not Copilot)

- Works offline with a local model; free tier requires no subscription or
  GitHub auth (Copilot needs a paid seat).
- Integrates as a standard `nvim-cmp` source (`cmp-tabnine`) rather than a
  parallel ghost-text engine, so it composes with LunarVim's existing cmp setup.

## Prior art in this repo

The dormant `lua/user/` tree already contains a working TabNine wiring — mine it
for the exact options rather than reinventing:

- `lua/user/plugins.lua` — the `tzachar/cmp-tabnine` lazy spec (flag-gated).
- `lua/user/builtin.lua` — registers `cmp_tabnine` in `lvim.builtin.cmp.sources`
  and adds a `menu` label via lspkind formatting.

Note: that tree is inert (nothing `require`s it). The rollout below re-expresses
the same wiring inside the active `config.lua`.

## Plugin

```lua
{
  "tzachar/cmp-tabnine",
  build = "./install.sh",              -- downloads the TabNine binary (network)
  dependencies = { "hrsh7th/nvim-cmp" },
  event = "InsertEnter",
}
```

`cmp-tabnine` works on Neovim 0.9 (the pinned Docker/CI image) and 0.11 (local),
so no version guard is needed.

## Wiring into LunarVim's cmp

1. Configure the source engine:

   ```lua
   require("cmp_tabnine.config").setup {
     max_lines = 1000,
     max_num_results = 3,
     sort = true,
     run_on_every_keystroke = true,
     show_prediction_strength = true,
   }
   ```

2. Register it as a cmp source **below** LSP priority so it never shadows real
   language-server completions:

   ```lua
   table.insert(lvim.builtin.cmp.sources, { name = "cmp_tabnine", priority = 100 })
   ```

3. Add a menu label so entries are visually distinct (LunarVim uses lspkind):

   ```lua
   lvim.builtin.cmp.formatting.source_names["cmp_tabnine"] = "(TN)"
   ```

## Opt-in flag (ship dormant)

Gate everything behind a custom flag so the feature lands disabled and is flipped
on intentionally (mirrors the dormant config's flag pattern):

```lua
lvim.builtin.tabnine = { active = false }

if lvim.builtin.tabnine.active then
  -- append the plugin spec + the cmp wiring above
end
```

## Compatibility & ops notes

- The `build = "./install.sh"` step pulls a platform binary from the network on
  first install; surface this in `bootstrap.sh` / the doctor check so an offline
  or sandboxed first-run fails loudly rather than silently.
- Free tier works out of the box. TabNine Pro (optional) is managed via
  `:CmpTabnineHub`.

## Rollout phases

1. **Land dormant** — add the flag (default `false`), plugin spec, and cmp
   wiring guarded by the flag. No behavior change; `:Lazy sync` still clean.
2. **Enable locally** — set `active = true`, run `:Lazy sync`, then confirm
   `(TN)`-labelled entries appear in the completion menu while typing Python.
3. **Tune** — adjust `max_num_results` / `priority` / `sort` so TabNine
   supplements LSP + LuaSnip instead of crowding them out; verify LSP items
   still rank first.

## Verification

- `:Lazy sync` installs `cmp-tabnine` and runs `install.sh` without error.
- `:CmpStatus` lists `cmp_tabnine` as an active source.
- Typing in a `.py` buffer shows `(TN)` suggestions ranked after LSP entries.
- Toggling `lvim.builtin.tabnine.active = false` + `make sync` fully removes it.
