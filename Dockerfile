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
    && curl -s https://raw.githubusercontent.com/LunarVim/LunarVim/release-1.3/neovim-0.9/utils/installer/install.sh \
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

# Install plugins headlessly
RUN /root/.local/bin/lvim --headless "+Lazy! sync" +qa 2>&1 || true

# Install Mason packages
RUN /root/.local/bin/lvim --headless \
    +"MasonInstall pyright bash-language-server shellcheck shfmt debugpy stylua lua-language-server" +q 2>&1 \
    || true

# Default: run headless config load test
CMD ["/root/.local/bin/lvim", "--headless", "-c", "lua print('config loaded ok')", "-c", "q"]
