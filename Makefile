.PHONY: help sync ubuntu ubuntu-64-bit macos-arm64 evals bootstrap doctor install uv-tool-install npm-tool-install

help: ## Show this help message
	@uv run python -c "import re; \
	[[print(f'\033[36m{m[0]:<20}\033[0m {m[1]}') for m in re.findall(r'^([a-zA-Z0-9_-]+):.*?## (.*)$$', open(makefile).read(), re.M)] for makefile in ('$(MAKEFILE_LIST)').strip().split()]"

sync: ## Sync config files from this repo to ~/.config/lvim/
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

install: uv-tool-install npm-tool-install ## Install all Python and Node.js CLI tools

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
