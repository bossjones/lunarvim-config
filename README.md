# lunarvim-config

A highly customized [LunarVim](https://www.lunarvim.org/) setup (built on the
`release-1.3/neovim-0.9` branch) that deploys to `~/.config/lvim/`.

Inspired by <https://github.com/abzcoding/lvim/tree/main>

## macOS Quick Start (Apple Silicon)

### Prerequisites

Per the [LunarVim install docs](https://www.lunarvim.org/docs/installation), you need
**Neovim v0.9.0+**, plus Git, Make, Python/pip, Node/npm, Cargo, and Ripgrep.

> **Neovim 0.9.0+ is a minimum, not a ceiling.** LunarVim 1.3 only *locks new installs to
> nvim 0.9+* — newer Neovim (0.10 / 0.11) works too. This config is used daily on 0.11.x.
> The few 0.9-specific bits (e.g. the snacks notifier in `config.lua`) are *defensively
> disabled* on newer Neovim rather than being hard failures.

[Homebrew](https://brew.sh) is the easiest way to get the prerequisites on macOS:

```bash
brew install neovim git make node ripgrep luarocks hadolint vale golangci-lint
# uv — the Python tool runner the Makefile uses: https://docs.astral.sh/uv/
# cargo (Rust), only if you want `selene`: https://rustup.rs
```

### Install

```bash
git clone https://github.com/bossjones/lunarvim-config.git
cd lunarvim-config

# 1. Install LunarVim itself (release-1.3/neovim-0.9 branch), if not already installed:
curl -fsSL --retry 5 --retry-delay 5 --retry-all-errors \
  https://raw.githubusercontent.com/LunarVim/LunarVim/release-1.3/neovim-0.9/utils/installer/install.sh \
  -o /tmp/lvim-install.sh
LV_BRANCH='release-1.3/neovim-0.9' bash /tmp/lvim-install.sh --install-dependencies -y

# 2. Deploy this config to ~/.config/lvim (zip-backs-up + moves the old config aside).
#    Preview the diff first, then apply:
make deploy ARGS=--dry-run
make deploy

# 3. Install linters, formatters, and LSP servers
#    (uv + npm + brew + go + luarocks + Mason; no sudo, brew step is skipped if absent):
make install

# 4. Verify the environment, then launch:
make doctor
lvim
```

### Notes on the commands

- **`make deploy`** (backend: `script/install.py`) backs up + moves the old config aside +
  copies the payload, and supports `--dry-run`. Prefer it over `make sync`, which is a plain
  `cp -av` that overwrites in place (and even copies `.git`).
- **`make install`** uses `uv tool` (no global `pip`, no `sudo luarocks`) and guards the brew
  step — it's the portable successor to `make macos-arm64`, which still exists as a legacy
  one-shot (uses `sudo luarocks install luacheck`, `cargo install selene`, and global `pip`).
- **`make bootstrap` (`./bootstrap.sh`) is *not* recommended on macOS.** Its Neovim-from-source
  step is gated to Linux (`uname -m` = `aarch64`; Apple Silicon reports `arm64`), so it never
  installs Neovim on a Mac, and its `fnm` bootstrap has hard-coded Linux `/home/developer`
  paths. Use the steps above instead.

Run `make help` to see all available targets.

## Structure

<details>
  <summary><strong>Structure</strong> <small><i>(🔎 Click to expand/collapse)</i></small></summary>

- [after/](./after) - Stuff that happens after
  - [ftplugin/](./after/ftplugin) - Language specific settings
  - [syntax/](./after/syntax) - Custom syntax for languages
- [ftdetect/](./ftdetect) - Let neovim identify custom filetypes
- [ftplugin/](./ftplugin) - Language specific custom settings
- [lsp-settings](./lsp-settings) - Custom lang server settings
- [lua/](./lua) - Lua plugin configurations
  - [telescope/](./lua/telescope/_extensions) - Telescope extensions
  - [user/](./lua/user) - User specific settings
    - [null_ls](./lua/user/null_ls) - list of configured linters/formatters
    - [autocommands.lua](./lua/user/autocommands.lua) - user defined autocommands
    - [builtin.lua](./lua/user/builtin.lua) - change internal lunarvim settings
    - [keybindings.lua](./lua/user/keybindings.lua) - user defined keybindings
    - [plugins.lua](./lua/user/plugins.lua) - list of installed plugins
    - [lsp_kind.lua](./lua/user/lsp_kind.lua) - all the icons and lsp ui goodies are here
    - [theme.lua](./lua/user/theme.lua) - customized themes
- [config.lua](./config.lua) - Main customization point for settings
- [snippets/](./snippets) - Personal code snippets

</details>

## Custom Key-mappings

Note that,

- **Leader** key set as <kbd>Space</kbd>

<details open>
  <summary>
    <strong>Key-mappings</strong>
    <small><i>(🔎 Click to expand/collapse)</i></small>
  </summary>

<center>Modes: 𝐍=normal 𝐕=visual 𝐒=select 𝐈=insert 𝐂=command</center>

### UI

| Key                                                           | Mode | Action              | Plugin or Mapping                             |
| ------------------------------------------------------------- | :--: | ------------------- | --------------------------------------------- |
| <kbd>Space</kbd>+<kbd>e</kbd>                                 |  𝐍   | Open file tree      | <small>NvimTree</small>                       |
| <kbd>Space</kbd>+<kbd>o</kbd>                                 |  𝐍   | Open symbols        | <small>Symbols-outline</small>                |
| <kbd>Space</kbd>+<kbd>f</kbd>                                 |  𝐍   | Open file finder    | <small>Telescope</small>                      |
| <kbd>Space</kbd>+<kbd>h</kbd>                                 |  𝐍   | Remove highlight    | <small>`nohlsearch<`</small>                  |
| <kbd>Space</kbd>+<kbd>/</kbd>                                 |  𝐍   | Toggle comment      | <small>Comment.nvim</small>                   |
| <kbd>Space</kbd>+<kbd>?</kbd>                                 |  𝐍   | Open cheats         | <small>cheat.sh</small>                       |
| <kbd>Space</kbd>+<kbd>'</kbd>                                 |  𝐍   | Open marks          | <small>which-key marks</small>                |
| <kbd>Space</kbd>+<kbd>z</kbd>                                 |  𝐍   | Zen mode            | <small>zen-mode.nvim</small>                  |
| <kbd>Space</kbd>+<kbd>P</kbd>                                 |  𝐍   | Projects            | <small>project.nvim</small>                   |
| <kbd>Ctrl</kbd>+<kbd>\</kbd>                                  | 𝐈 𝐍  | Open terminal       | <small>toggleterm.nvim</small>                |
| <kbd>Alt</kbd>+<kbd>0</kbd>                                   | 𝐈 𝐍  | Vertical terminal   | <small>toggleterm.nvim</small>                |
| <kbd>Ctrl</kbd>+<kbd>s</kbd>                                  |  𝐈   | Show signature help | <small>`vim.lsp.buf.signature_help()`</small> |
| <kbd>Alt</kbd>+<kbd>s</kbd>                                   |  𝐈   | Snippet selection   | <small>Telescope luasnip extension</small>    |
| <kbd>Space</kbd>+<kbd>C</kbd> or <kbd>Ctrl</kbd>+<kbd>P</kbd> |  𝐍   | Command Palette     | <small>legendary.nvim</small>                 |

### Motion

| Key                         | Mode | Action                  | Plugin or Mapping                                             |
| --------------------------- | :--: | ----------------------- | ------------------------------------------------------------- |
| <kbd>f</kbd>                |  𝐍   | find next character     | <small>HopChar1CurrentLineAC</small> or <small>leap_f</small> |
| <kbd>F</kbd>                |  𝐍   | find previous character | <small>HopChar1CurrentLineBC</small> or <small>leap_F</small> |
| <kbd>s</kbd>                |  𝐍   | find character          | <small>HopChar2MW</small> or <small>leap_s</small>            |
| <kbd>S</kbd>                |  𝐍   | find word               | <small>HopWordMW</small> or <small>leap_S</small>             |
| <kbd>Alt</kbd>+<kbd>a</kbd> |  𝐈   | select all              | <small>ggVG</small>                                           |
| <kbd>Alt</kbd>+<kbd>a</kbd> |  𝐍   | increment number        | <small>C-A</small>                                            |
| <kbd>Alt</kbd>+<kbd>x</kbd> |  𝐍   | decrement number        | <small>C-X</small>                                            |

### LSP

| Key                                                                                      | Mode | Action                              |
| ---------------------------------------------------------------------------------------- | :--: | ----------------------------------- |
| <kbd>Tab</kbd> / <kbd>Shift-Tab</kbd>                                                    |  𝐈   | Navigate completion-menu            |
| <kbd>Enter</kbd>                                                                         |  𝐈   | Select completion or expand snippet |
| <kbd>Up</kbd>or <kbd>Down</kbd>                                                          |  𝐈   | Movement in completion pop-up       |
| <kbd>]</kbd>+<kbd>d</kbd>                                                                |  𝐍   | Next diagnostic                     |
| <kbd>[</kbd>+<kbd>d</kbd>                                                                |  𝐍   | Previous diagnostic                 |
| <kbd>Space</kbd>+<kbd>l</kbd>+<kbd>j</kbd> or <kbd>Space</kbd>+<kbd>l</kbd>+<kbd>k</kbd> |  𝐍   | Next/previous LSP diagnostic        |
| <kbd>Space</kbd>+<kbd>l</kbd>+<kbd>r</kbd>                                               |  𝐍   | replace current word in project     |
| <kbd>Ctrl</kbd>+<kbd>e</kbd>                                                             |  𝐈   | Close pop-up                        |
| <kbd>Tab</kbd> / <kbd>Shift-Tab</kbd>                                                    | 𝐈 𝐒  | Navigate snippet placeholders       |
| <kbd>Space</kbd>+<kbd>l</kbd>                                                            |  𝐍   | keybindings for lsp                 |
| <kbd>g</kbd>+<kbd>a</kbd>                                                                |  𝐍   | code actions                        |
| <kbd>g</kbd>+<kbd>A</kbd>                                                                |  𝐍   | codelens actions                    |
| <kbd>g</kbd>+<kbd>d</kbd>                                                                |  𝐍   | goto definition                     |
| <kbd>g</kbd>+<kbd>t</kbd>                                                                |  𝐍   | goto type definition                |
| <kbd>g</kbd>+<kbd>D</kbd>                                                                |  𝐍   | goto declaration                    |
| <kbd>g</kbd>+<kbd>I</kbd>                                                                |  𝐍   | goto implementation                 |
| <kbd>g</kbd>+<kbd>p</kbd>                                                                |  𝐍   | peek implementation                 |
| <kbd>g</kbd>+<kbd>r</kbd>                                                                |  𝐍   | goto references                     |
| <kbd>g</kbd>+<kbd>s</kbd>                                                                |  𝐍   | show signature help                 |

### Plugin: AsyncTasks

| Key                                        | Mode | Action        |
| ------------------------------------------ | :--: | ------------- |
| <kbd>Space</kbd>+<kbd>m</kbd>+<kbd>f</kbd> |  𝐍   | Build File    |
| <kbd>Space</kbd>+<kbd>m</kbd>+<kbd>p</kbd> |  𝐍   | Build Project |
| <kbd>Space</kbd>+<kbd>m</kbd>+<kbd>e</kbd> |  𝐍   | Edit Tasks    |
| <kbd>Space</kbd>+<kbd>m</kbd>+<kbd>l</kbd> |  𝐍   | List Tasks    |
| <kbd>Space</kbd>+<kbd>r</kbd>+<kbd>f</kbd> |  𝐍   | Run File      |
| <kbd>Space</kbd>+<kbd>r</kbd>+<kbd>p</kbd> |  𝐍   | Run Project   |

### Plugin: Gitsigns

| Key                                                                                      | Mode | Action                 |
| ---------------------------------------------------------------------------------------- | :--: | ---------------------- |
| <kbd>Space</kbd>+<kbd>g</kbd>+<kbd>j</kbd> or <kbd>Space</kbd>+<kbd>g</kbd>+<kbd>k</kbd> |  𝐍   | Next/previous Git hunk |
| <kbd>Space</kbd>+<kbd>g</kbd>+<kbd>p</kbd>                                               |  𝐍   | Preview hunk           |
| <kbd>Space</kbd>+<kbd>g</kbd>+<kbd>l</kbd>                                               |  𝐍   | Blame line             |
| <kbd>Space</kbd>+<kbd>g</kbd>+<kbd>s</kbd>                                               | 𝐍 𝐕  | Stage hunk             |
| <kbd>Space</kbd>+<kbd>g</kbd>+<kbd>u</kbd>                                               |  𝐍   | Undo stage hunk        |
| <kbd>Space</kbd>+<kbd>g</kbd>+<kbd>d</kbd>                                               |  𝐍   | Diff to head           |
| <kbd>Space</kbd>+<kbd>g</kbd>+<kbd>h</kbd>                                               |  𝐍   | Buffer git history     |
| <kbd>Space</kbd>+<kbd>g</kbd>+<kbd>R</kbd>                                               | 𝐍 𝐕  | Reset hunk             |

### Plugin: LazyGit

| Key                                        | Mode | Action           |
| ------------------------------------------ | :--: | ---------------- |
| <kbd>Space</kbd>+<kbd>g</kbd>+<kbd>g</kbd> |  𝐍   | Open lazy git UI |

### Plugin: Telescope

| Key                                        | Mode | Action                     |
| ------------------------------------------ | :--: | -------------------------- |
| <kbd>Space</kbd>+<kbd>f</kbd>              |  𝐍   | File search                |
| <kbd>Space</kbd>+<kbd>P</kbd>              |  𝐍   | Project search             |
| <kbd>Space</kbd>+<kbd>s</kbd>+<kbd>s</kbd> |  𝐍   | Grep search                |
| <kbd>Space</kbd>+<kbd>s</kbd>+<kbd>f</kbd> |  𝐍   | Telescope find_files       |
| <kbd>Space</kbd>+<kbd>s</kbd>+<kbd>e</kbd> |  𝐍   | Telescope file_browser     |
| <kbd>Space</kbd>+<kbd>F</kbd>+<kbd>l</kbd> |  𝐍   | Reopen last search         |
| <kbd>Space</kbd>+<kbd>b</kbd>+<kbd>f</kbd> |  𝐍   | Buffers                    |
| <kbd>Space</kbd>+<kbd>s</kbd>+<kbd>c</kbd> |  𝐍   | Colorschemes               |
| <kbd>Space</kbd>+<kbd>s</kbd>+<kbd>C</kbd> |  𝐍   | Command history            |
| <kbd>Space</kbd>+<kbd>s</kbd>+<kbd>h</kbd> |  𝐍   | Find help                  |
| <kbd>Space</kbd>+<kbd>s</kbd>+<kbd>k</kbd> |  𝐍   | Keymap search              |
| <kbd>Space</kbd>+<kbd>s</kbd>+<kbd>M</kbd> |  𝐍   | Man Pages search           |
| <kbd>Space</kbd>+<kbd>s</kbd>+<kbd>r</kbd> |  𝐍   | Register search            |
| <kbd>Space</kbd>+<kbd>s</kbd>+<kbd>t</kbd> |  𝐕   | Grep string under cursor   |
| <kbd>Space</kbd>+<kbd>s</kbd>+<kbd>t</kbd> |  𝐍   | Grep raw                   |
| <kbd>Space</kbd>+<kbd>F</kbd>+<kbd>b</kbd> |  𝐍   | Builtin search             |
| <kbd>Space</kbd>+<kbd>F</kbd>+<kbd>f</kbd> |  𝐍   | Current buffer search      |
| <kbd>Space</kbd>+<kbd>F</kbd>+<kbd>g</kbd> |  𝐍   | Git files search           |
| <kbd>Space</kbd>+<kbd>F</kbd>+<kbd>i</kbd> |  𝐍   | Installed plugins          |
| <kbd>Space</kbd>+<kbd>F</kbd>+<kbd>p</kbd> |  𝐍   | Project search             |
| <kbd>Space</kbd>+<kbd>F</kbd>+<kbd>i</kbd> |  𝐍   | Installed plugins          |
| **in _Telescope_ window**                  |      |                            |
| <kbd>CR</kbd>                              | 𝐈 𝐍  | Multi/Single Open          |
| <kbd>Ctrl</kbd>+<kbd>c</kbd>               | 𝐈 𝐍  | Exit telescope             |
| <kbd>Ctrl</kbd>+<kbd>v</kbd>               | 𝐈 𝐍  | Open in a vertical split   |
| <kbd>Ctrl</kbd>+<kbd>s</kbd>               | 𝐈 𝐍  | Open in a split            |
| <kbd>Ctrl</kbd>+<kbd>t</kbd>               | 𝐈 𝐍  | Open in a tab              |
| <kbd>Ctrl</kbd>+<kbd>b</kbd>               |  𝐈   | Go back in Command Palette |
| <kbd>Tab</kbd>                             | 𝐈 𝐍  | Toggle Selection + Next    |
| <kbd>Shift</kbd>+<kbd>Tab</kbd>            | 𝐈 𝐍  | Toggle Selection + Prev    |

### Plugin: Harpoon

| Key                               | Mode | Action                           |
| --------------------------------- | :--: | -------------------------------- |
| <kbd>Space</kbd>+<kbd>Space</kbd> |  𝐍   | Show harpoon shortlist           |
| <kbd>Space</kbd>+<kbd>a</kbd>     |  𝐍   | Add file to shortlist            |
| <kbd>Space</kbd>+<kbd>1</kbd>     |  𝐍   | Jump to first file on shortlist  |
| <kbd>Space</kbd>+<kbd>2</kbd>     |  𝐍   | Jump to second file on shortlist |
| <kbd>Space</kbd>+<kbd>3</kbd>     |  𝐍   | Jump to third file on shortlist  |
| <kbd>Space</kbd>+<kbd>4</kbd>     |  𝐍   | Jump to forth file on shortlist  |

### Plugin: Neogen

| Key                                        | Mode | Action                 |
| ------------------------------------------ | :--: | ---------------------- |
| <kbd>Space</kbd>+<kbd>n</kbd>+<kbd>c</kbd> |  𝐍   | Class documentation    |
| <kbd>Space</kbd>+<kbd>n</kbd>+<kbd>f</kbd> |  𝐍   | Function documentation |
| <kbd>Space</kbd>+<kbd>n</kbd>+<kbd>t</kbd> |  𝐍   | Type documentation     |
| <kbd>Space</kbd>+<kbd>n</kbd>+<kbd>F</kbd> |  𝐍   | File documentation     |

### Plugin: Persistence

| Key                                        | Mode | Action                                |
| ------------------------------------------ | :--: | ------------------------------------- |
| <kbd>Space</kbd>+<kbd>q</kbd>+<kbd>d</kbd> |  𝐍   | Quit without saving session           |
| <kbd>Space</kbd>+<kbd>q</kbd>+<kbd>l</kbd> |  𝐍   | Restore last session                  |
| <kbd>Space</kbd>+<kbd>q</kbd>+<kbd>s</kbd> |  𝐍   | Restore last session from current dir |

### Plugin: Bufferline

| Key                                        | Mode | Action               |
| ------------------------------------------ | :--: | -------------------- |
| <kbd>Shift</kbd>+<kbd>x</kbd>              |  𝐍   | Close buffer         |
| <kbd>Space</kbd>+<kbd>b</kbd>+<kbd>f</kbd> |  𝐍   | Find buffer          |
| <kbd>Space</kbd>+<kbd>b</kbd>+<kbd>b</kbd> |  𝐍   | Toggle buffer groups |
| <kbd>Space</kbd>+<kbd>b</kbd>+<kbd>p</kbd> |  𝐍   | Toggle pin           |
| <kbd>Space</kbd>+<kbd>b</kbd>+<kbd>s</kbd> |  𝐍   | Pick buffer          |
| <kbd>Space</kbd>+<kbd>b</kbd>+<kbd>1</kbd> |  𝐍   | Goto buffer 1        |
| <kbd>Space</kbd>+<kbd>b</kbd>+<kbd>h</kbd> |  𝐍   | Close all to left    |
| <kbd>Space</kbd>+<kbd>b</kbd>+<kbd>l</kbd> |  𝐍   | Close all to right   |
| <kbd>Space</kbd>+<kbd>b</kbd>+<kbd>D</kbd> |  𝐍   | Sort by directory    |
| <kbd>Space</kbd>+<kbd>b</kbd>+<kbd>L</kbd> |  𝐍   | Sort by language     |

### Plugin: Trouble

| Key                                        | Mode | Action                |
| ------------------------------------------ | :--: | --------------------- |
| <kbd>Space</kbd>+<kbd>T</kbd>+<kbd>d</kbd> |  𝐍   | Diagnostics           |
| <kbd>Space</kbd>+<kbd>T</kbd>+<kbd>f</kbd> |  𝐍   | Definitions           |
| <kbd>Space</kbd>+<kbd>T</kbd>+<kbd>r</kbd> |  𝐍   | References            |
| <kbd>Space</kbd>+<kbd>T</kbd>+<kbd>t</kbd> |  𝐍   | Todo                  |
| <kbd>Space</kbd>+<kbd>T</kbd>+<kbd>w</kbd> |  𝐍   | Workspace diagnostics |

### Plugin: Ultest

| Key                                        | Mode | Action                  |
| ------------------------------------------ | :--: | ----------------------- |
| <kbd>Space</kbd>+<kbd>t</kbd>+<kbd>f</kbd> |  𝐍   | Run all tests in a file |
| <kbd>Space</kbd>+<kbd>t</kbd>+<kbd>n</kbd> |  𝐍   | Only run nearest test   |
| <kbd>Space</kbd>+<kbd>t</kbd>+<kbd>s</kbd> |  𝐍   | Open test summary       |

### Plugin: Neotest

| Key                                        | Mode | Action                       |
| ------------------------------------------ | :--: | ---------------------------- |
| <kbd>Space</kbd>+<kbd>t</kbd>+<kbd>a</kbd> |  𝐍   | Run all tests                |
| <kbd>Space</kbd>+<kbd>t</kbd>+<kbd>f</kbd> |  𝐍   | Run tests in a file          |
| <kbd>Space</kbd>+<kbd>t</kbd>+<kbd>r</kbd> |  𝐍   | Only run nearest test        |
| <kbd>Space</kbd>+<kbd>t</kbd>+<kbd>s</kbd> |  𝐍   | Open test summary            |
| <kbd>Space</kbd>+<kbd>t</kbd>+<kbd>o</kbd> |  𝐍   | Open test output             |
| <kbd>Space</kbd>+<kbd>t</kbd>+<kbd>w</kbd> |  𝐍   | Watch test                   |
| <kbd>Space</kbd>+<kbd>t</kbd>+<kbd>x</kbd> |  𝐍   | Stop test                    |
| <kbd>Space</kbd>+<kbd>t</kbd>+<kbd>n</kbd> |  𝐍   | Jump to next failed test     |
| <kbd>Space</kbd>+<kbd>t</kbd>+<kbd>p</kbd> |  𝐍   | Jump to previous failed test |
| <kbd>Space</kbd>+<kbd>t</kbd>+<kbd>c</kbd> |  𝐍   | Cancel test                  |

### Plugin: Spectre

| Key                                        | Mode | Action                         |
| ------------------------------------------ | :--: | ------------------------------ |
| <kbd>Space</kbd>+<kbd>R</kbd>+<kbd>p</kbd> |  𝐍   | Replace word in project        |
| <kbd>Space</kbd>+<kbd>R</kbd>+<kbd>w</kbd> |  𝐍   | Replace visually selected word |
| <kbd>Space</kbd>+<kbd>R</kbd>+<kbd>f</kbd> |  𝐍   | Replace word in current buffer |

### Plugin: SSR

| Key                                        | Mode | Action                                          |
| ------------------------------------------ | :--: | ----------------------------------------------- |
| <kbd>Space</kbd>+<kbd>r</kbd>              |  𝐕   | Structural replace confirm using `<leader><cr>` |
| <kbd>Space</kbd>+<kbd>R</kbd>+<kbd>s</kbd> |  𝐍   | Structural replace confirm using `<leader><cr>` |

### Plugin: Copilot

| Key                          | Mode | Action                              |
| ---------------------------- | :--: | ----------------------------------- |
| <kbd>Ctrl</kbd>+<kbd>h</kbd> |  𝐈   | `copilot#Accept("<CR>")`            |
| <kbd>Ctrl</kbd>+<kbd>e</kbd> |  𝐈   | Close cmp menu                      |
| <kbd>Ctrl</kbd>+<kbd>]</kbd> |  𝐈   | `<Plug>(copilot-dismiss)`           |
| <kbd>Alt</kbd>+<kbd>]</kbd>  |  𝐈   | `<Plug>(copilot-next)`              |
| <kbd>Alt</kbd>+<kbd>[</kbd>  |  𝐈   | `<Plug>(copilot-previous)`          |
| <kbd>Alt</kbd>+<kbd>\</kbd>  |  𝐈   | `"<Cmd>vertical Copilot panel<CR>"` |

### Plugin: Lsp_Lines

| Key                           | Mode | Action                   |
| ----------------------------- | :--: | ------------------------ |
| <kbd>Space</kbd>+<kbd>v</kbd> |  𝐍   | Toggle showing lsp_lines |

### Plugin: Overseer

| Key                                        | Mode | Action           |
| ------------------------------------------ | :--: | ---------------- |
| <kbd>Space</kbd>+<kbd>r</kbd>+<kbd>f</kbd> |  𝐍   | Run              |
| <kbd>Space</kbd>+<kbd>r</kbd>+<kbd>p</kbd> |  𝐍   | Run with cmd     |
| <kbd>Space</kbd>+<kbd>r</kbd>+<kbd>t</kbd> |  𝐍   | Toggle output    |
| <kbd>Space</kbd>+<kbd>m</kbd>+<kbd>n</kbd> |  𝐍   | New Task         |
| <kbd>Space</kbd>+<kbd>m</kbd>+<kbd>l</kbd> |  𝐍   | Load Task Bundle |
| <kbd>Space</kbd>+<kbd>m</kbd>+<kbd>s</kbd> |  𝐍   | Save Task Bundle |
| <kbd>Space</kbd>+<kbd>m</kbd>+<kbd>q</kbd> |  𝐍   | Quick Action     |
| <kbd>Space</kbd>+<kbd>m</kbd>+<kbd>f</kbd> |  𝐍   | Task Action      |

### Plugin: NeoTree

| Key                           | Mode | Action                           |
| ----------------------------- | :--: | -------------------------------- |
| <kbd>Space</kbd>+<kbd>e</kbd> |  𝐍   | Toggle tree                      |
| <kbd>></kbd> and <kbd><</kbd> |  𝐍   | Next and prev source inside tree |
| <kbd>Enter</kbd>              |  𝐍   | Open                             |
| <kbd>s</kbd>                  |  𝐍   | Open in vertical split           |
| <kbd>S</kbd>                  |  𝐍   | Open in horizontal spit          |
| <kbd>H</kbd>                  |  𝐍   | Toggle hidden files              |
| <kbd>a</kbd>                  |  𝐍   | Add files/dirs                   |
| <kbd>A</kbd>                  |  𝐍   | Add new dir                      |
| <kbd>r</kbd>                  |  𝐍   | Rename                           |
| <kbd>h</kbd>                  |  𝐍   | Go Updir                         |
| <kbd>l</kbd>                  |  𝐍   | Open                             |
| <kbd>P</kbd>                  |  𝐍   | Toggle preview                   |
| <kbd>/</kbd>                  |  𝐍   | Fuzzy finder                     |

### Plugin: Mind

| Key                                        | Mode | Action            |
| ------------------------------------------ | :--: | ----------------- |
| <kbd>Space</kbd>+<kbd>M</kbd>+<kbd>M</kbd> |  𝐍   | Open Main Tree    |
| <kbd>Space</kbd>+<kbd>M</kbd>+<kbd>m</kbd> |  𝐍   | Open Local Tree   |
| <kbd>Enter</kbd>                           |  𝐍   | open data         |
| <kbd>Tab</kbd>                             |  𝐍   | toggle node       |
| <kbd>Shift</kbd>+<kbd>Tab</kbd>            |  𝐍   | toggle parent     |
| <kbd>/</kbd>                               |  𝐍   | select path       |
| <kbd>$</kbd>                               |  𝐍   | change icons menu |
| <kbd>c</kbd>                               |  𝐍   | create new node   |
| <kbd>q</kbd>                               |  𝐍   | quit              |

</details>

### Linters & Formatters

The canonical way to install every linter, formatter, and LSP server is a single target — it
chains `uv` (Python), `npm`, `brew`, `go`, `luarocks`, the Vale config copy, and Mason:

```shell
make install
```

`make install` also handles the Vale config (`vale_config.ini` → `~/.vale.ini` plus
`~/.config/vale/styles/`) via its `copy-configs` sub-target — no manual copy needed.

The legacy one-shot installer still exists if you prefer it (uses `sudo luarocks`,
`cargo install selene`, and global `pip`):

```shell
make macos-arm64   # macOS (Apple Silicon)
make ubuntu        # Ubuntu (arm64)
make ubuntu-64-bit # Ubuntu (x86_64)
```

For LaTeX support:

```shell
# brew install --cask mactex-no-gui  # macOS
# or install zathura and chktex on Linux
```

In case you want a better tex support in mac, check
[this](tex-support) out

if you want the custom `gostructhelper`, first get the pkg:

```shell
cd /tmp
git clone https://github.com/vanhtuan0409/gostructhelper.git
cd gostructhelper/cmds/gostructhelper
go build -o /usr/local/bin/gostructhelper && chmod 0755 /usr/local/bin/gostructhelper
```

</details>

## Developer

### CI

This repo uses GitHub Actions (`.github/workflows/ci.yml`) with two jobs:

- **Lint** — runs `luacheck`, `stylua --check`, `shellcheck`, and `markdownlint`
- **LunarVim headless** — installs LunarVim and loads the config in headless mode

### `/commit-push-pr` — Stage, Commit, Push, and Open a PR

The `/commit-push-pr` command (defined in `.claude/commands/commit-push-pr.md`) automates the full git workflow from staged changes to an open pull request:

1. **Inspect** — runs `git status` and `git diff` to understand what changed
2. **Stage** — adds specific modified/untracked files (skips secrets like `.env`)
3. **Commit** — generates a conventional commit message (`feat`, `fix`, `chore`, etc.) with a Co-Authored-By footer
4. **Push** — pushes to remote, setting upstream (`-u`) if the branch is new
5. **PR** — runs `gh pr create` with a Summary and Test plan body

**Usage** (inside Claude Code):

```text
/commit-push-pr
```

**Prerequisites**: `gh` CLI authenticated (`gh auth login`).

### `/debug-ci` — Automated CI Failure Repair

The `/debug-ci` command (defined in `.claude/commands/debug-ci.md`) is a Claude Code slash command that automates the full CI debugging loop:

1. **Diagnose** — finds the latest failed run via `gh`, downloads failed logs, categorizes failures
2. **Plan** — maps each failure type to a fix strategy
3. **Fix** — applies targeted edits (or runs `stylua .` for formatting)
4. **Local validation** — runs the same lint checks CI runs, iterates up to 3 times
5. **Commit & push** — stages specific files, uses conventional commit prefixes
6. **Remote verification** — polls GitHub Actions by commit SHA until the new run completes

The command supports up to 3 outer retry cycles and guards against checking stale runs.

**Usage** (inside Claude Code):

```text
/debug-ci
/debug-ci <run-id>
```

**Prerequisites**: `gh` CLI authenticated, and ideally `luacheck`, `stylua`, `shellcheck`, and `markdownlint` installed locally for the validation phase.

### Running Evals

Eval test cases for `/debug-ci` live in `.claude/commands/debug-ci/evals/evals.json`. There are three scenarios:

| Test | Description |
| ------ | ------------- |
| `luacheck_failure` | Injects an undefined global + unused variable, expects diagnosis and fix |
| `stylua_formatting_drift` | Introduces bad indentation, expects `stylua .` auto-format |
| `no_failures_clean_exit` | All runs green, expects early exit with no changes |

To run evals with the Claude Code CLI:

```bash
make evals
# or directly:
claude-code eval .claude/commands/debug-ci/evals/evals.json
```

Each test case defines `setup` commands (to inject failures), `teardown` commands (to restore files), and `expected_behaviors` that are checked against the command output.

---
