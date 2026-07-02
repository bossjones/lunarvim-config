"""Shared fixtures for the testinfra suite.

These tests validate the `lunarvim-config:test` Docker image: that the expected
binaries and LSP servers are installed, that the config loads headlessly, and
that devops filetypes are detected with their treesitter parsers compiled.

Run with:  uv run pytest tests/testinfra -v
The `make test-testinfra` target builds the image first (docker-build dep).
If the image is missing, the fixture builds it automatically.
"""

from __future__ import annotations

import base64
import subprocess
from pathlib import Path

import pytest
import testinfra

IMAGE = "lunarvim-config:test"
LVIM = "/root/.local/bin/lvim"
REPO_ROOT = Path(__file__).resolve().parents[2]

# Candidate Neovim/LunarVim data dirs where Mason installs packages.
# LunarVim's stdpath("data") is ~/.local/share/lvim (confirmed in-image); the
# others are fallbacks in case the runtime layout changes.
DATA_DIR_CANDIDATES = (
    "/root/.local/share/lvim",
    "/root/.local/share/lunarvim",
    "/root/.local/share/nvim",
)


def _image_exists() -> bool:
    result = subprocess.run(
        ["docker", "image", "inspect", IMAGE],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


@pytest.fixture(scope="session")
def host():
    """A testinfra host backed by a running container of the built image."""
    if not _image_exists():
        subprocess.run(
            ["docker", "build", "-t", IMAGE, "."],
            cwd=REPO_ROOT,
            check=True,
        )

    container_id = subprocess.check_output(
        ["docker", "run", "-d", "--rm", IMAGE, "sleep", "infinity"],
        text=True,
    ).strip()
    try:
        yield testinfra.get_host(f"docker://{container_id}")
    finally:
        subprocess.run(
            ["docker", "rm", "-f", container_id],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )


@pytest.fixture(scope="session")
def mason_packages(host):
    """Return the Mason `packages/` dir that actually exists in the image."""
    for base in DATA_DIR_CANDIDATES:
        pkg_dir = f"{base}/mason/packages"
        if host.file(pkg_dir).exists:
            return pkg_dir
    pytest.fail(
        "No Mason packages dir found in image; tried: "
        + ", ".join(f"{b}/mason/packages" for b in DATA_DIR_CANDIDATES)
    )


@pytest.fixture(scope="session")
def run_lua(host):
    """Return a callable that runs Lua inside the loaded LunarVim config.

    The Lua is base64-encoded to sidestep shell quoting, written to /tmp, and
    executed via `luafile` after config.lua has been sourced at startup. Have
    your Lua `io.write` a uniquely-marked token so tests can parse it out of the
    noisy headless output.
    """

    def _run(lua_code: str):
        encoded = base64.b64encode(lua_code.encode()).decode()
        host.run("echo %s | base64 -d > /tmp/probe.lua", encoded)
        return host.run(
            "%s --headless -c 'luafile /tmp/probe.lua' -c 'qa!'", LVIM
        )

    return _run
