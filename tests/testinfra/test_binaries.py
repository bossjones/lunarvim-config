"""Assert the toolchain the config depends on is present in the image."""

from __future__ import annotations

import pytest

# Tools that must resolve on PATH inside the container.
# - nvim: symlinked to /usr/local/bin/nvim
# - lvim / uv / uvx: in /root/.local/bin (on PATH via Dockerfile ENV)
# - basedpyright(+langserver) / ruff: installed via `uv tool install`
PATH_BINARIES = [
    "nvim",
    "lvim",
    "uv",
    "uvx",
    "ruff",
    "basedpyright",
    "basedpyright-langserver",
]

# Mason packages that must be installed (names match `MasonInstall` args and the
# on-disk directory names under mason/packages/).
MASON_PACKAGES = [
    "bash-language-server",
    "yaml-language-server",
    "json-lsp",
    "taplo",
    "dockerfile-language-server",
    "shellcheck",
    "shfmt",
    "debugpy",
    "stylua",
    "lua-language-server",
]


@pytest.mark.parametrize("binary", PATH_BINARIES)
def test_binary_on_path(host, binary):
    assert host.exists(binary), f"{binary} not found on PATH in the image"


def test_lvim_binary_file(host):
    assert host.file("/root/.local/bin/lvim").exists


@pytest.mark.parametrize("package", MASON_PACKAGES)
def test_mason_package_installed(host, mason_packages, package):
    pkg = host.file(f"{mason_packages}/{package}")
    assert pkg.exists and pkg.is_directory, (
        f"Mason package '{package}' not installed under {mason_packages}"
    )


def test_pyright_not_installed_via_mason(host, mason_packages):
    """pyright was fully replaced by basedpyright; it should not linger in Mason."""
    assert not host.file(f"{mason_packages}/pyright").exists
