# Force amd64: Neovim 0.9.5 only has x86_64 Linux tarballs.
# On Apple Silicon, Docker Desktop handles emulation via Rosetta.
ARG BUILDPLATFORM=linux/amd64
FROM --platform=linux/amd64 ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV HOME=/root
ENV PATH="/root/.local/bin:/root/.cargo/bin:${PATH}"

SHELL ["/bin/bash", "-c"]

# System dependencies (Node.js 18 via NodeSource — Ubuntu 22.04 ships v12 which is too old)
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl gnupg \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
       | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_18.x nodistro main" \
       > /etc/apt/sources.list.d/nodesource.list \
    && apt-get update && apt-get install -y --no-install-recommends \
    git wget unzip \
    build-essential \
    python3 python3-pip python3-venv \
    nodejs \
    luarocks \
    shellcheck \
    && rm -rf /var/lib/apt/lists/*

# Install Neovim 0.9.5 (pinned to match CI)
RUN curl -LO https://github.com/neovim/neovim/releases/download/v0.9.5/nvim-linux64.tar.gz \
    && tar xzf nvim-linux64.tar.gz -C /opt \
    && ln -s /opt/nvim-linux64/bin/nvim /usr/local/bin/nvim \
    && rm nvim-linux64.tar.gz

# Install uv (official Docker method)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Install Rust (minimal profile — LunarVim installer checks for cargo)
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal

# Pre-install LunarVim runtime deps
RUN pip3 install pynvim \
    && npm install -g neovim tree-sitter-cli

# Install LunarVim (deps already installed above)
RUN mkdir -p /root/.local/bin \
    && curl -fsSL --retry 5 --retry-delay 5 --retry-all-errors \
       https://raw.githubusercontent.com/LunarVim/LunarVim/release-1.3/neovim-0.9/utils/installer/install.sh \
       -o /tmp/install-lvim.sh \
    && LV_BRANCH='release-1.3/neovim-0.9' bash /tmp/install-lvim.sh -y \
    && rm /tmp/install-lvim.sh

# Install luacheck
RUN luarocks install luacheck

# Copy config into the container
WORKDIR /root/lunarvim-config
COPY . .

# Sync config to LunarVim location (skip .git which is excluded by .dockerignore)
RUN for item in Makefile config.lua lsp-settings ftplugin README.md after .vale \
      .luarc.json .luacheckrc .markdownlint.json ftdetect snippets lua .stylua.toml \
      .gitignore LICENSE; do \
      [ -e "$item" ] && cp -a "$item" /root/.config/lvim/; \
    done

# Install plugins headlessly.
# 1. LunarVim 1.3's first-time setup leaves a dead `null-ls.nvim.cloning` behind
#    (the pinned jose-elias-alvarez/null-ls.nvim repo was deleted upstream); config.lua
#    disables it and installs the nvimtools/none-ls fork instead. Remove the stale
#    half-clone so the plugin dir is clean.
# 2. `Lazy! sync` alone does NOT block until clones finish under headless nvim, leaving
#    plugins (snacks, none-ls, neotest, ...) half-installed. `sync{wait=true}` blocks
#    until every clone/build completes, making the image a faithful test target.
RUN LAZY_OPT=/root/.local/share/lunarvim/site/pack/lazy/opt; \
    find "$LAZY_OPT" -maxdepth 1 -name '*.cloning' -exec rm -rf {} + 2>/dev/null || true; \
    /root/.local/bin/lvim --headless \
    -c "lua require('lazy').sync({ wait = true, show = false })" -c "qa" 2>&1 || true

# Install Python LSP/CLI tools globally via uv (uv/uvx copied in above).
# basedpyright is the Python LSP (types); ruff runs as its own LSP (`ruff server`)
# for lint + format. Both configured in ftplugin/python.lua.
RUN uv tool install basedpyright && uv tool install ruff

# Install Mason packages (non-Python LSP servers + shell/lua tooling).
# Every server referenced by an ftplugin is installed here so the image is a
# faithful test target for the testinfra suite.
RUN /root/.local/bin/lvim --headless \
    +"MasonInstall bash-language-server yaml-language-server json-lsp taplo dockerfile-language-server shellcheck shfmt debugpy stylua lua-language-server" +q 2>&1 \
    || true

# Regenerate LunarVim's per-filetype LSP templates against the SYNCED config.
# LunarVim generates them during install with its default skip list (which does
# NOT skip pyright), baking a python template that auto-installs+attaches pyright.
# Regenerating with our config (pyright skipped) drops it, so only the uv-installed
# basedpyright + ruff (set up in ftplugin/python.lua) attach.
RUN /root/.local/bin/lvim --headless \
    -c "lua require('lvim.lsp.templates').remove_template_files()" \
    -c "lua require('lvim.lsp.templates').generate_templates()" -c "qa" 2>&1 \
    || true

# Pre-compile treesitter parsers headlessly (compiled with cc). Only parsers that
# exist in the pinned nvim-treesitter are listed — xml and ssh_config are NOT
# available on the nvim-0.9 pin, so XML/.plist and ~/.ssh/config use Neovim's
# builtin syntax highlighting instead (no parser needed).
RUN /root/.local/bin/lvim --headless \
    +"TSInstallSync bash python lua json jsonc yaml toml ini dockerfile" +qa 2>&1 \
    || true

# Default: run headless config load test
CMD ["/root/.local/bin/lvim", "--headless", "-c", "lua print('config loaded ok')", "-c", "q"]
