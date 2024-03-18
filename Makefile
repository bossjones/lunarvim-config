sync:
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

ubuntu:
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
# 	cp -av ~/.config/lvim/.vale ~/.config/vale
# # fix the address inside .vale.ini
# 	cp -a ~/.config/lvim/vale_config.ini ~/.vale.ini

ubuntu-64-bit:
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

macos-arm64:
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

bootstrap:
	./bootstrap.sh
