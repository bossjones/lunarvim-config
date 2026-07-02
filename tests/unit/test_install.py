"""Fast unit tests for script/install.py.

Everything runs against tmp_path with an injected fixed timestamp, so no test touches
the real repo or $HOME. See specs/install.md for the behavior these lock in.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

TS = "20260702-120000"  # injected fixed timestamp


def _action(plan, rel_path: str):
    """Return the single FileAction whose rel_path matches, or None."""
    for a in plan.actions:
        if a.rel_path == rel_path:
            return a
    return None


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------

def test_manifest_excludes_git_and_repo_meta(install):
    manifest = set(install.MANIFEST)
    expected = {
        "Makefile", "config.lua", "README.md", ".luarc.json", ".luacheckrc",
        ".markdownlint.json", ".stylua.toml", ".gitignore", "LICENSE",
        "lsp-settings", "ftplugin", "after", ".vale", "ftdetect", "snippets", "lua",
    }
    assert manifest == expected, f"unexpected manifest: {manifest ^ expected}"
    for forbidden in (".git", "pyproject.toml", "tests", "specs", "bootstrap.sh", "Dockerfile"):
        assert forbidden not in manifest


# ---------------------------------------------------------------------------
# build_plan classification
# ---------------------------------------------------------------------------

def test_build_plan_all_create_on_empty_target(install, fake_repo, tmp_path):
    target = tmp_path / "lvim"  # does not exist
    plan = install.build_plan(fake_repo, target)
    assert plan.actions, "expected actions"
    assert all(a.kind is install.ActionKind.CREATE for a in plan.actions)
    # 9 manifest files + 7 dirs * 1 nested file each = 16 leaf files
    assert len(plan.actions) == 16


def test_build_plan_unchanged_for_identical_file(install, fake_repo, tmp_path):
    target = tmp_path / "lvim"
    target.mkdir()
    (target / "config.lua").write_text("content of config.lua\n", encoding="utf-8")

    plan = install.build_plan(fake_repo, target)
    action = _action(plan, "config.lua")
    assert action is not None
    assert action.kind is install.ActionKind.UNCHANGED
    assert action.diff == ""


def test_build_plan_overwrite_has_unified_diff(install, fake_repo, tmp_path):
    target = tmp_path / "lvim"
    target.mkdir()
    (target / "config.lua").write_text("old contents\n", encoding="utf-8")

    plan = install.build_plan(fake_repo, target)
    action = _action(plan, "config.lua")
    assert action is not None
    assert action.kind is install.ActionKind.OVERWRITE
    for marker in ("---", "+++", "@@"):
        assert marker in action.diff


def test_binary_helper_detects_nul(install, tmp_path):
    binary = tmp_path / "bin"
    binary.write_bytes(b"\x00\x01\x02binary")
    text = tmp_path / "txt"
    text.write_text("just text\n", encoding="utf-8")
    assert install._is_binary(binary) is True
    assert install._is_binary(text) is False


def test_build_plan_binary_file_marked_no_diff(install, fake_repo, tmp_path):
    # Make a manifest file binary in both repo and target.
    (fake_repo / "config.lua").write_bytes(b"\x00\x01new")
    target = tmp_path / "lvim"
    target.mkdir()
    (target / "config.lua").write_bytes(b"\x00\x01old")

    plan = install.build_plan(fake_repo, target)
    action = _action(plan, "config.lua")
    assert action is not None
    assert action.is_binary is True
    assert action.kind is install.ActionKind.OVERWRITE
    assert action.diff == ""


# ---------------------------------------------------------------------------
# backup_existing
# ---------------------------------------------------------------------------

def test_backup_creates_zip(install, tmp_path):
    target = tmp_path / "lvim"
    (target / ".git").mkdir(parents=True)
    (target / ".git" / "HEAD").write_text("ref\n", encoding="utf-8")
    (target / "config.lua").write_text("cfg\n", encoding="utf-8")
    backups = tmp_path / "lvim-backups"

    zip_path, _moved = install.backup_existing(target, backups, TS)

    assert zip_path == backups / f"lvim-backup-{TS}.zip"
    assert zip_path.is_file()
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
    assert any(n.endswith("config.lua") for n in names)
    assert not any(".git" in n for n in names), f".git leaked into zip: {names}"


def test_backup_moves_target_aside(install, tmp_path):
    target = tmp_path / "lvim"
    target.mkdir()
    (target / "config.lua").write_text("cfg\n", encoding="utf-8")
    backups = tmp_path / "lvim-backups"

    _zip, moved_to = install.backup_existing(target, backups, TS)

    assert moved_to == target.parent / f"lvim.bak.{TS}"
    assert moved_to.is_dir()
    assert (moved_to / "config.lua").is_file()
    assert not target.exists()


def test_backup_noop_when_target_missing(install, tmp_path):
    target = tmp_path / "lvim"  # does not exist
    backups = tmp_path / "lvim-backups"

    zip_path, moved_to = install.backup_existing(target, backups, TS)

    assert zip_path is None
    assert moved_to is None
    assert not backups.exists()


# ---------------------------------------------------------------------------
# apply_plan fidelity
# ---------------------------------------------------------------------------

def test_apply_copies_every_manifest_item(install, fake_repo, tmp_path):
    target = tmp_path / "lvim"
    install.apply_plan(fake_repo, target)

    for name in install.MANIFEST_FILES:
        assert (target / name).is_file()
        assert (target / name).read_bytes() == (fake_repo / name).read_bytes()
    for name in install.MANIFEST_DIRS:
        assert (target / name / "nested.lua").is_file()


def test_git_not_deployed(install, fake_repo, tmp_path):
    target = tmp_path / "lvim"
    install.apply_plan(fake_repo, target)
    assert not (target / ".git").exists()


# ---------------------------------------------------------------------------
# main / CLI
# ---------------------------------------------------------------------------

def _snapshot(root: Path) -> dict[str, bytes]:
    return {
        str(p.relative_to(root)): p.read_bytes()
        for p in root.rglob("*")
        if p.is_file()
    }


def test_dry_run_makes_no_filesystem_changes(install, fake_repo, tmp_path):
    target = tmp_path / ".config" / "lvim"
    target.mkdir(parents=True)
    (target / "config.lua").write_text("old\n", encoding="utf-8")
    before = _snapshot(target)

    rc = install.main(["--dry-run", "--target", str(target), "--repo", str(fake_repo)])

    assert rc == 0
    assert _snapshot(target) == before
    assert not (tmp_path / ".config" / "lvim-backups").exists()
    # No move-aside dir should have been created during a dry run.
    assert not list((tmp_path / ".config").glob("lvim.bak.*"))


def test_exit_code_zero_on_success(install, fake_repo, tmp_path):
    target = tmp_path / ".config" / "lvim"
    rc = install.main(["--yes", "--target", str(target), "--repo", str(fake_repo)])
    assert rc == 0
    assert (target / "config.lua").is_file()


def test_exit_code_two_on_bad_repo(install, tmp_path):
    target = tmp_path / ".config" / "lvim"
    rc = install.main(["--yes", "--repo", str(tmp_path / "nope"), "--target", str(target)])
    assert rc == 2
