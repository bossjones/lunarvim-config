"""Fixtures for the fast (no-Docker) unit suite covering scripts under script/.

The scripts are PEP 723 files under `script/`, not importable packages, so we load
them as modules via importlib fixtures. A second fixture builds a small fake repo tree
in `tmp_path` so tests never touch the real repo or `$HOME`.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
INSTALL_PY = REPO_ROOT / "script" / "install.py"
SMOKE_PY = REPO_ROOT / "script" / "smoke.py"


@pytest.fixture(scope="session")
def install():
    """Load script/install.py as a module and return it."""
    spec = importlib.util.spec_from_file_location("lvim_install", INSTALL_PY)
    assert spec is not None and spec.loader is not None, f"cannot load {INSTALL_PY}"
    module = importlib.util.module_from_spec(spec)
    # Register before exec so dataclasses can resolve cls.__module__ (needed on 3.14+).
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def smoke():
    """Load script/smoke.py as a module and return it."""
    spec = importlib.util.spec_from_file_location("lvim_smoke", SMOKE_PY)
    assert spec is not None and spec.loader is not None, f"cannot load {SMOKE_PY}"
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def fake_repo(tmp_path: Path, install) -> Path:
    """Create a repo dir populated with every MANIFEST item (plus a .git that must
    NOT be deployed). Files get known text content; dirs get a nested file each."""
    repo = tmp_path / "repo"
    repo.mkdir()

    for name in install.MANIFEST_FILES:
        (repo / name).write_text(f"content of {name}\n", encoding="utf-8")

    for name in install.MANIFEST_DIRS:
        d = repo / name
        d.mkdir(parents=True)
        (d / "nested.lua").write_text(f"-- {name}/nested.lua\n", encoding="utf-8")

    # A .git dir that the installer must ignore.
    git = repo / ".git"
    git.mkdir()
    (git / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")

    return repo
