# lunarvim-config
My attempt to configure lunarvim correctly, this is a POC and will be moved to zsh-dotfiles

Inspired by https://github.com/abzcoding/lvim/tree/main


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


### Recommended Linters

You can use [mason](mason) to install these:

```shell
brew install luarocks
luarocks install luacheck  # if you want to use luacheck
cargo install selene  # if you want to use selene instead of luacheck
brew install hadolint  # if you want to lint dockerfiles
pip install vim-vint  # for vim linting
# install llvm and clang_format for clang stuff
npm install -g @fsouza/prettierd # if you want to use prettierd
pip install yapf flake8 black  # for python stuff
# if you want to use the markdown thingy
brew install vale markdownlint-cli
cp -r ~/.config/lvim/.vale ~/.config/vale
# fix the address inside .vale.ini
cp ~/.config/lvim/vale_config.ini ~/.vale.ini
# if you want the latex stuff
# brew install --cask mactex-no-gui # for mac
# or install zathura and chktex on linux
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

---
