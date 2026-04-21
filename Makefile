.PHONY: help backup sync ubuntu ubuntu-64-bit macos-arm64 evals bootstrap doctor install uv-tool-install npm-tool-install brew-tool-install go-tool-install luarocks-tool-install copy-configs mason-tool-install test docker-build docker-test docker-lint docker-shell

help: ## Show this help message
	@uv run python -c "import re; \
	[[print(f'\033[36m{m[0]:<20}\033[0m {m[1]}') for m in re.findall(r'^([a-zA-Z0-9_-]+):.*?## (.*)$$', open(makefile).read(), re.M)] for makefile in ('$(MAKEFILE_LIST)').strip().split()]"

backup: ## Create a timestamped zip backup of ~/.config/lvim/
	@if [ -d "$$HOME/.config/lvim" ]; then \
		mkdir -p "$$HOME/.config/lvim-backups" && \
		zip -r "$$HOME/.config/lvim-backups/lvim-backup-$$(date +%Y%m%d-%H%M%S).zip" "$$HOME/.config/lvim" \
			-x "$$HOME/.config/lvim/.git/*" && \
		echo "Backup saved to $$HOME/.config/lvim-backups/"; \
	else \
		echo "No ~/.config/lvim/ directory found — skipping backup."; \
	fi

sync: backup ## Sync config files from this repo to ~/.config/lvim/
	cp -av Makefile ~/.config/lvim/
	cp -av config.lua ~/.config/lvim/
	cp -av lsp-settings ~/.config/lvim/
	cp -av ftplugin ~/.config/lvim/
	cp -av README.md ~/.config/lvim/
	cp -av .git ~/.config/lvim/
	cp -av after ~/.config/lvim/
	cp -av .vale ~/.config/lvim/
	cp -av .luarc.json ~/.config/lvim/
	cp -av .luacheckrc ~/.config/lvim/
	cp -av .markdownlint.json ~/.config/lvim/
	cp -av ftdetect ~/.config/lvim/
	cp -av snippets ~/.config/lvim/
	cp -av lua ~/.config/lvim/
	cp -av .stylua.toml ~/.config/lvim/
	cp -av .gitignore ~/.config/lvim/
	cp -av LICENSE ~/.config/lvim/

ubuntu: ## Install linters and formatters on Ubuntu (arm64)
	sudo apt install luarocks -y
	sudo luarocks install luacheck
	curl -L 'https://github.com/hadolint/hadolint/releases/download/v2.12.0/hadolint-Linux-arm64' > ~/.local/bin/hadolint && \
	chmod +x ~/.local/bin/hadolint && \
	pip install vim-vint && \
	npm install -g @fsouza/prettierd && \
	pip install yapf flake8 black && \
	wget https://github.com/errata-ai/vale/releases/download/v2.26.0/vale_2.26.0_Linux_arm64.tar.gz -O vale.tar.gz && \
	tar -xvzf vale.tar.gz -C ~/.local/bin && \
	rm vale.tar.gz && \
	npm install -g markdownlint-cli

ubuntu-64-bit: ## Install linters and formatters on Ubuntu (x86_64)
	sudo apt install luarocks -y
	sudo luarocks install luacheck
	curl -L 'https://github.com/hadolint/hadolint/releases/download/v2.12.0/hadolint-Linux-x86_64' > ~/.local/bin/hadolint && \
	chmod +x ~/.local/bin/hadolint && \
	pip install vim-vint && \
	npm install -g @fsouza/prettierd && \
	pip install yapf flake8 black && \
	wget https://github.com/errata-ai/vale/releases/download/v3.0.7/vale_3.0.7_Linux_64-bit.tar.gz -O vale.tar.gz && \
	tar -xvzf vale.tar.gz -C ~/.local/bin && \
	rm vale.tar.gz && \
	npm install -g markdownlint-cli

macos-arm64: ## Install linters and formatters on macOS (Apple Silicon)
	brew install luarocks
# if you want to use luacheck
	sudo luarocks install luacheck
# if you want to use selene instead of luacheck
	cargo install selene
# if you want to lint dockerfiles
	brew install hadolint
# for vim linting
	pip install vim-vint
# install llvm and clang_format for clang stuff
# if you want to use prettierd
	npm install -g @fsouza/prettierd
# for python stuff
	pip install autoflake autopep8 better_exceptions black bpython flake8 isort pylint rich ruff yapf
# if you want to use the markdown thingy
	brew install vale markdownlint-cli


# ~/dev/bossjones/lunarvim-config main*
# ❯ luarocks list

# Rocks installed for Lua 5.4
# ---------------------------

# argparse
#    0.7.1-1 (installed) - /opt/homebrew/lib/luarocks/rocks-5.4

# luacheck
#    1.1.0-1 (installed) - /opt/homebrew/lib/luarocks/rocks-5.4

# luafilesystem
#    1.8.0-1 (installed) - /opt/homebrew/lib/luarocks/rocks-5.4

evals: ## Run Claude Code evals
	claude-code eval .claude/commands/debug-ci/evals/evals.json

bootstrap: ## Full bootstrap (install LunarVim + dependencies)
	./bootstrap.sh

doctor: ## Check environment health (binaries, linters, LSP, configs)
	@uv run script/doctor.py

install: uv-tool-install npm-tool-install brew-tool-install go-tool-install luarocks-tool-install copy-configs mason-tool-install ## Install all tools, configs, and LSP servers

uv-tool-install: ## Install Python CLI tools globally via uv tool
	uv tool install autoflake
	uv tool install autopep8
	uv tool install black
	uv tool install flake8
	uv tool install isort
	uv tool install pylint
	uv tool install ruff
	uv tool install vim-vint
	uv tool install yapf

npm-tool-install: ## Install Node.js CLI tools globally via npm
	npm install -g @fsouza/prettierd
	npm install -g markdownlint-cli

brew-tool-install: ## Install CLI tools via Homebrew (requires brew in PATH)
	@if command -v brew >/dev/null 2>&1; then \
		brew install hadolint vale golangci-lint; \
	else \
		echo "brew not found in PATH — skipping brew-tool-install (install Homebrew: https://brew.sh)"; \
	fi

go-tool-install: ## Install Go CLI tools
	go install golang.org/x/tools/cmd/goimports@latest
	go install github.com/mgechev/revive@latest

luarocks-tool-install: ## Install Lua linting tools via luarocks
	luarocks install luacheck

copy-configs: ## Copy config files (vale, etc.) to their expected locations
	@cp -v vale_config.ini ~/.vale.ini
	@mkdir -p ~/.config/vale/styles && cp -av .vale/* ~/.config/vale/styles/

mason-tool-install: ## Install Mason LSP/tool packages via LunarVim
	lvim --headless +"MasonInstall pyright bash-language-server shellcheck shfmt debugpy stylua lua-language-server" +q

test: ## Run Lua unit tests via plenary (headless)
	nvim --headless -u tests/minimal_init.lua \
		-c "PlenaryBustedDirectory tests/ {minimal_init = 'tests/minimal_init.lua', sequential = true}"

docker-build: ## Build Docker validation image
	docker build -t lunarvim-config:test .

docker-test: docker-build ## Build and run headless config validation in Docker
	docker run --rm lunarvim-config:test
	docker run --rm lunarvim-config:test /root/.local/bin/lvim --headless \
		-c "lua print('snacks loaded: ' .. tostring(pcall(require, 'snacks')))" -c q
	@echo "Docker validation passed."

docker-lint: docker-build ## Run luacheck inside Docker
	docker run --rm lunarvim-config:test luacheck . --globals lvim vim Snacks

docker-shell: docker-build ## Open interactive shell in the Docker container
	docker run --rm -it lunarvim-config:test /bin/bash
