#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["rich>=13.0"]
# ///
"""Environment health check for the lunarvim-config repository.

Usage:
    uv run script/doctor.py

Checks that all required files, binaries, linters, formatters, Mason LSP
packages, and Python packages are present and correctly configured.

Exit code 0 = all REQUIRED checks pass.
Exit code 1 = one or more REQUIRED checks failed.
"""

from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


class Severity(Enum):
    REQUIRED = "REQUIRED"
    RECOMMENDED = "RECOMMENDED"
    OPTIONAL = "OPTIONAL"


class Status(Enum):
    OK = "OK"
    WARN = "WARN"
    ERROR = "ERROR"


@dataclass
class CheckResult:
    name: str
    status: Status
    severity: Severity
    category: str
    message: str
    fix_hint: str = ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _repo_root() -> Path:
    """Return the repository root (parent of script/)."""
    return Path(__file__).resolve().parent.parent


def _is_darwin() -> bool:
    return platform.system() == "Darwin"


def _arch() -> str:
    machine = platform.machine().lower()
    if machine in ("arm64", "aarch64"):
        return "arm64"
    return "x86_64"


def _has_bin(name: str) -> bool:
    return shutil.which(name) is not None


def _mason_base() -> Path:
    xdg = os.environ.get("XDG_DATA_HOME", "")
    if xdg:
        return Path(xdg) / "lvim" / "mason"
    return Path.home() / ".local" / "share" / "lvim" / "mason"


# ---------------------------------------------------------------------------
# Version detection
# ---------------------------------------------------------------------------

# LunarVim 1.4 is the branch documented for Neovim 0.9.x (master needs 0.10+).
EXPECTED_LVIM_BRANCH = "release-1.4/neovim-0.9"

# The Docker/CI image pins 0.9.5; local machines run much newer. Both must work.
MIN_NVIM_VERSION = (0, 9, 0)

_NVIM_VERSION_RE = re.compile(r"NVIM\s+v(\d+)\.(\d+)\.(\d+)")
_LUA_LINE_COMMENT_RE = re.compile(r"^[ \t]*--.*$", re.MULTILINE)
_LUA_COMMIT_RE = re.compile(r'commit\s*=\s*"([0-9a-fA-F]{7,40})"')

_NONE_LS_MARKER = '"nvimtools/none-ls.nvim"'


def _parse_nvim_version(text: str) -> tuple[int, int, int] | None:
    """Extract (major, minor, patch) from `nvim --version` output."""
    m = _NVIM_VERSION_RE.search(text)
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def _parse_none_ls_pin(config_text: str) -> str | None:
    """Return the `commit` SHA pinned on the none-ls spec in config.lua, if any.

    Lua line comments are stripped first so a commented-out SHA can't be mistaken for
    the real pin, and the search window stops at the next top-level `lvim.plugins`
    entry so an unpinned none-ls can't inherit the following plugin's commit.
    """
    text = _LUA_LINE_COMMENT_RE.sub("", config_text)
    start = text.find(_NONE_LS_MARKER)
    if start == -1:
        return None

    window = text[start:]
    end = window.find("\n  {", 1)
    if end != -1:
        window = window[:end]

    m = _LUA_COMMIT_RE.search(window)
    return m.group(1) if m else None


def _run(args: list[str]) -> str | None:
    """Run a command and return its stripped stdout, or None if it fails."""
    try:
        out = subprocess.run(
            args, capture_output=True, text=True, timeout=10, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip() or None


def _lvim_runtime_dir() -> Path:
    """LunarVim's runtime dir, honoring $LUNARVIM_RUNTIME_DIR like the `lvim` wrapper."""
    env = os.environ.get("LUNARVIM_RUNTIME_DIR", "")
    if env:
        return Path(env)
    return Path.home() / ".local" / "share" / "lunarvim"


def _nvim_version() -> tuple[int, int, int] | None:
    out = _run(["nvim", "--version"])
    return _parse_nvim_version(out) if out else None


def _lvim_git_info() -> tuple[str | None, str | None]:
    """Return (branch, tag) of the installed LunarVim runtime."""
    base = _lvim_runtime_dir() / "lvim"
    if not (base / ".git").exists():
        return None, None
    branch = _run(["git", "-C", str(base), "rev-parse", "--abbrev-ref", "HEAD"])
    tag = _run(["git", "-C", str(base), "describe", "--tags", "--abbrev=0"])
    return branch, tag


def _none_ls_installed_commit() -> str | None:
    """HEAD of the none-ls checkout Lazy actually manages."""
    d = _lvim_runtime_dir() / "site" / "pack" / "lazy" / "opt" / "none-ls.nvim"
    if not (d / ".git").exists():
        return None
    return _run(["git", "-C", str(d), "rev-parse", "HEAD"])


# ---------------------------------------------------------------------------
# Check functions
# ---------------------------------------------------------------------------


def check_versions(repo: Path) -> list[CheckResult]:
    """Report installed Neovim/LunarVim versions and none-ls drift.

    none-ls gets its own check because LunarVim's snapshots/default.json pins it to a
    2023 revision that crashes on Neovim 0.11; config.lua overrides that pin, but the
    override only takes effect once the plugin is actually re-checked-out.
    """
    results: list[CheckResult] = []
    category = "Versions"

    # --- Neovim ---------------------------------------------------------
    nvim = _nvim_version()
    min_str = ".".join(str(n) for n in MIN_NVIM_VERSION)
    if nvim is None:
        results.append(
            CheckResult(
                "Neovim", Status.ERROR, Severity.REQUIRED, category,
                "not found (or version unparseable)",
                "Install Neovim: https://neovim.io",
            )
        )
    else:
        ver = ".".join(str(n) for n in nvim)
        if nvim < MIN_NVIM_VERSION:
            results.append(
                CheckResult(
                    "Neovim", Status.ERROR, Severity.REQUIRED, category,
                    f"v{ver} is below the required v{min_str}",
                    f"Upgrade Neovim to v{min_str} or newer",
                )
            )
        else:
            results.append(
                CheckResult(
                    "Neovim", Status.OK, Severity.REQUIRED, category,
                    f"v{ver} (>= v{min_str})",
                )
            )

    # --- LunarVim -------------------------------------------------------
    branch, tag = _lvim_git_info()
    if branch is None:
        results.append(
            CheckResult(
                "LunarVim", Status.WARN, Severity.RECOMMENDED, category,
                f"runtime not found at {_lvim_runtime_dir() / 'lvim'}",
                "Run: make bootstrap   (or install LunarVim manually)",
            )
        )
    elif branch != EXPECTED_LVIM_BRANCH:
        results.append(
            CheckResult(
                "LunarVim", Status.WARN, Severity.RECOMMENDED, category,
                f"on '{branch}'{f' ({tag})' if tag else ''}; this repo targets '{EXPECTED_LVIM_BRANCH}'",
                f"Reinstall with LV_BRANCH='{EXPECTED_LVIM_BRANCH}'",
            )
        )
    else:
        results.append(
            CheckResult(
                "LunarVim", Status.OK, Severity.RECOMMENDED, category,
                f"{tag or 'unknown'} on {branch}",
            )
        )

    # --- none-ls revision ------------------------------------------------
    config_lua = repo / "config.lua"
    pin = (
        _parse_none_ls_pin(config_lua.read_text(encoding="utf-8"))
        if config_lua.is_file()
        else None
    )
    installed = _none_ls_installed_commit()

    if pin is None:
        results.append(
            CheckResult(
                "none-ls revision", Status.WARN, Severity.RECOMMENDED, category,
                "config.lua does not pin none-ls",
                "LunarVim's snapshot pin (3a48266) crashes on Neovim 0.11 — pin it in config.lua",
            )
        )
    elif installed is None:
        results.append(
            CheckResult(
                "none-ls revision", Status.WARN, Severity.RECOMMENDED, category,
                "not installed yet",
                "Launch 'lvim' once, then run: make plugins-update",
            )
        )
    elif installed == pin:
        results.append(
            CheckResult(
                "none-ls revision", Status.OK, Severity.RECOMMENDED, category,
                f"{installed[:7]} matches the config.lua pin",
            )
        )
    else:
        results.append(
            CheckResult(
                "none-ls revision", Status.WARN, Severity.RECOMMENDED, category,
                f"installed {installed[:7]} != config.lua pin {pin[:7]}",
                "Run: make plugins-update",
            )
        )

    return results



def check_source_files(repo: Path) -> list[CheckResult]:
    """Verify that the source files/dirs referenced by `make sync` exist."""
    results: list[CheckResult] = []
    category = "Source Files"

    files = [
        "Makefile",
        "config.lua",
        "README.md",
        ".luarc.json",
        ".luacheckrc",
        ".markdownlint.json",
        ".stylua.toml",
        ".gitignore",
        "LICENSE",
    ]
    dirs = [
        "lsp-settings",
        "ftplugin",
        "after",
        ".vale",
        "ftdetect",
        "snippets",
        "lua",
        ".git",
    ]

    for name in files:
        p = repo / name
        if p.is_file():
            results.append(
                CheckResult(name, Status.OK, Severity.REQUIRED, category, "present")
            )
        else:
            results.append(
                CheckResult(
                    name,
                    Status.ERROR,
                    Severity.REQUIRED,
                    category,
                    "missing",
                    f"Ensure '{name}' exists in the repo root",
                )
            )

    for name in dirs:
        p = repo / name
        if p.is_dir():
            results.append(
                CheckResult(
                    name + "/", Status.OK, Severity.REQUIRED, category, "present"
                )
            )
        else:
            results.append(
                CheckResult(
                    name + "/",
                    Status.ERROR,
                    Severity.REQUIRED,
                    category,
                    "missing",
                    f"Ensure '{name}/' directory exists in the repo root",
                )
            )

    return results


def check_target_dirs() -> list[CheckResult]:
    """Check that the LunarVim config target directory exists."""
    results: list[CheckResult] = []
    category = "Target Dirs"

    lvim_config = Path.home() / ".config" / "lvim"
    if lvim_config.is_dir():
        results.append(
            CheckResult(
                "~/.config/lvim/", Status.OK, Severity.REQUIRED, category, "present"
            )
        )
    else:
        results.append(
            CheckResult(
                "~/.config/lvim/",
                Status.ERROR,
                Severity.REQUIRED,
                category,
                "missing — LunarVim not installed?",
                "Run: make bootstrap   (or install LunarVim manually)",
            )
        )

    return results


def check_core_binaries() -> list[CheckResult]:
    """Check for core required binaries."""
    results: list[CheckResult] = []
    category = "Core Binaries"

    bins = {
        "nvim": "Install Neovim: https://neovim.io",
        "lvim": "Run: make bootstrap",
        "git": "Install git from your package manager",
        "make": "Install make (Xcode CLT on macOS, build-essential on Linux)",
        "node": "Install Node.js via fnm or nvm",
        "npm": "Installed with Node.js",
        "python3": "Install Python 3.10+",
        "pip3": "Installed with Python 3",
    }

    for name, hint in bins.items():
        if _has_bin(name):
            results.append(
                CheckResult(name, Status.OK, Severity.REQUIRED, category, "found")
            )
        else:
            results.append(
                CheckResult(
                    name, Status.ERROR, Severity.REQUIRED, category, "not found", hint
                )
            )

    return results


def check_package_managers() -> list[CheckResult]:
    """Check for optional/recommended package managers."""
    results: list[CheckResult] = []
    category = "Package Managers"

    checks: list[tuple[str, Severity, str]] = [
        ("cargo", Severity.RECOMMENDED, "Install Rust: https://rustup.rs"),
        (
            "luarocks",
            Severity.RECOMMENDED,
            "brew install luarocks" if _is_darwin() else "apt install luarocks",
        ),
        ("fnm", Severity.OPTIONAL, "Install fnm: https://github.com/Schniz/fnm"),
    ]
    if _is_darwin():
        checks.append(
            ("brew", Severity.RECOMMENDED, "Install Homebrew: https://brew.sh")
        )

    for name, severity, hint in checks:
        if _has_bin(name):
            results.append(CheckResult(name, Status.OK, severity, category, "found"))
        else:
            st = Status.WARN if severity != Severity.REQUIRED else Status.ERROR
            results.append(CheckResult(name, st, severity, category, "not found", hint))

    return results


def check_formatters() -> list[CheckResult]:
    """Check for formatters referenced by null_ls config."""
    results: list[CheckResult] = []
    category = "Formatters"

    # OR-logic: prettierd OR prettier
    if _has_bin("prettierd") or _has_bin("prettier"):
        found = "prettierd" if _has_bin("prettierd") else "prettier"
        results.append(
            CheckResult(
                "prettierd / prettier",
                Status.OK,
                Severity.RECOMMENDED,
                category,
                f"found ({found})",
            )
        )
    else:
        results.append(
            CheckResult(
                "prettierd / prettier",
                Status.WARN,
                Severity.RECOMMENDED,
                category,
                "neither found",
                "npm install -g @fsouza/prettierd",
            )
        )

    simple: list[tuple[str, Severity, str]] = [
        ("stylua", Severity.RECOMMENDED, "cargo install stylua"),
        ("black", Severity.RECOMMENDED, "uv tool install black"),
        ("isort", Severity.RECOMMENDED, "uv tool install isort"),
        ("ruff", Severity.RECOMMENDED, "uv tool install ruff"),
        (
            "shfmt",
            Severity.RECOMMENDED,
            "brew install shfmt" if _is_darwin() else "apt install shfmt",
        ),
        ("gofmt", Severity.OPTIONAL, "Install Go: https://go.dev/dl/"),
        (
            "goimports",
            Severity.OPTIONAL,
            "go install golang.org/x/tools/cmd/goimports@latest",
        ),
    ]

    for name, severity, hint in simple:
        if _has_bin(name):
            results.append(CheckResult(name, Status.OK, severity, category, "found"))
        else:
            st = Status.WARN
            results.append(CheckResult(name, st, severity, category, "not found", hint))

    return results


def check_linters() -> list[CheckResult]:
    """Check for linters referenced by null_ls config."""
    results: list[CheckResult] = []
    category = "Linters"

    # OR-logic: luacheck OR selene
    if _has_bin("luacheck") or _has_bin("selene"):
        found = "luacheck" if _has_bin("luacheck") else "selene"
        results.append(
            CheckResult(
                "luacheck / selene",
                Status.OK,
                Severity.RECOMMENDED,
                category,
                f"found ({found})",
            )
        )
    else:
        hint = "sudo luarocks install luacheck  OR  cargo install selene"
        results.append(
            CheckResult(
                "luacheck / selene",
                Status.WARN,
                Severity.RECOMMENDED,
                category,
                "neither found",
                hint,
            )
        )

    simple: list[tuple[str, Severity, str]] = [
        (
            "shellcheck",
            Severity.RECOMMENDED,
            "brew install shellcheck" if _is_darwin() else "apt install shellcheck",
        ),
        (
            "hadolint",
            Severity.RECOMMENDED,
            "brew install hadolint"
            if _is_darwin()
            else "Download from https://github.com/hadolint/hadolint/releases",
        ),
        (
            "vale",
            Severity.RECOMMENDED,
            "brew install vale"
            if _is_darwin()
            else "Download from https://github.com/errata-ai/vale/releases",
        ),
        ("markdownlint", Severity.RECOMMENDED, "npm install -g markdownlint-cli"),
        ("flake8", Severity.RECOMMENDED, "uv tool install flake8"),
        ("vint", Severity.RECOMMENDED, "uv tool install vim-vint"),
        (
            "golangci-lint",
            Severity.OPTIONAL,
            "brew install golangci-lint"
            if _is_darwin()
            else "https://golangci-lint.run/usage/install/",
        ),
        ("revive", Severity.OPTIONAL, "go install github.com/mgechev/revive@latest"),
    ]

    for name, severity, hint in simple:
        if _has_bin(name):
            results.append(CheckResult(name, Status.OK, severity, category, "found"))
        else:
            st = Status.WARN
            results.append(CheckResult(name, st, severity, category, "not found", hint))

    return results


def check_config_files() -> list[CheckResult]:
    """Check for expected config files outside the repo."""
    results: list[CheckResult] = []
    category = "Config Files"

    vale_ini = Path.home() / ".vale.ini"
    if vale_ini.is_file():
        results.append(
            CheckResult(
                "~/.vale.ini", Status.OK, Severity.RECOMMENDED, category, "present"
            )
        )
    else:
        results.append(
            CheckResult(
                "~/.vale.ini",
                Status.WARN,
                Severity.RECOMMENDED,
                category,
                "missing",
                "cp vale_config.ini ~/.vale.ini",
            )
        )

    revive_toml = Path.home() / ".config" / "revive.toml"
    if revive_toml.is_file():
        results.append(
            CheckResult(
                "~/.config/revive.toml",
                Status.OK,
                Severity.OPTIONAL,
                category,
                "present",
            )
        )
    else:
        results.append(
            CheckResult(
                "~/.config/revive.toml",
                Status.WARN,
                Severity.OPTIONAL,
                category,
                "missing (only needed for Go)",
                "",
            )
        )

    return results


def check_mason_packages() -> list[CheckResult]:
    """Check that Mason-installed LSP servers/tools are present."""
    results: list[CheckResult] = []
    category = "Mason/LSP"

    mason_bin = _mason_base() / "bin"

    # (mason bin name, severity). Note some Mason packages install a binary
    # whose name differs from the package name (json-lsp -> vscode-json-language-server,
    # dockerfile-language-server -> docker-langserver).
    mason_install = (
        "bash-language-server yaml-language-server json-lsp taplo "
        "dockerfile-language-server shellcheck shfmt debugpy stylua lua-language-server"
    )
    packages: list[tuple[str, Severity]] = [
        ("bash-language-server", Severity.RECOMMENDED),
        ("yaml-language-server", Severity.RECOMMENDED),
        ("vscode-json-language-server", Severity.RECOMMENDED),
        ("taplo", Severity.RECOMMENDED),
        ("docker-langserver", Severity.RECOMMENDED),
        ("lua-language-server", Severity.RECOMMENDED),
        ("shellcheck", Severity.RECOMMENDED),
        ("shfmt", Severity.RECOMMENDED),
        ("debugpy", Severity.RECOMMENDED),
        ("stylua", Severity.RECOMMENDED),
    ]

    if not mason_bin.is_dir():
        for name, severity in packages:
            results.append(
                CheckResult(
                    f"mason:{name}",
                    Status.WARN,
                    severity,
                    category,
                    "Mason bin dir not found",
                    f'Run: lvim --headless +"MasonInstall {mason_install}" +q',
                )
            )
    else:
        for name, severity in packages:
            bin_path = mason_bin / name
            if bin_path.exists():
                results.append(
                    CheckResult(
                        f"mason:{name}", Status.OK, severity, category, "installed"
                    )
                )
            else:
                results.append(
                    CheckResult(
                        f"mason:{name}",
                        Status.WARN,
                        severity,
                        category,
                        "not installed",
                        f'lvim --headless +"MasonInstall {name}" +q',
                    )
                )

    # basedpyright is the Python LSP, installed globally via `uv tool install`
    # (not Mason), so it resolves on PATH rather than in the Mason bin dir.
    if _has_bin("basedpyright"):
        results.append(
            CheckResult(
                "basedpyright",
                Status.OK,
                Severity.RECOMMENDED,
                category,
                "installed (uv tool)",
            )
        )
    else:
        results.append(
            CheckResult(
                "basedpyright",
                Status.WARN,
                Severity.RECOMMENDED,
                category,
                "not found",
                "uv tool install basedpyright",
            )
        )

    return results


def check_python_packages() -> list[CheckResult]:
    """Check for Python CLI tools installed globally via `uv tool install`."""
    results: list[CheckResult] = []
    category = "Python Packages"

    # (uv tool/package name, binary it puts on PATH, install hint)
    packages: list[tuple[str, str, str]] = [
        ("black", "black", "uv tool install black"),
        ("ruff", "ruff", "uv tool install ruff"),
        ("flake8", "flake8", "uv tool install flake8"),
        ("isort", "isort", "uv tool install isort"),
        ("pylint", "pylint", "uv tool install pylint"),
        ("yapf", "yapf", "uv tool install yapf"),
        ("autopep8", "autopep8", "uv tool install autopep8"),
        ("autoflake", "autoflake", "uv tool install autoflake"),
        ("vim-vint", "vint", "uv tool install vim-vint"),
    ]

    for pkg, bin_name, hint in packages:
        if _has_bin(bin_name):
            results.append(
                CheckResult(
                    f"uv:{pkg}", Status.OK, Severity.RECOMMENDED, category, "installed"
                )
            )
        else:
            results.append(
                CheckResult(
                    f"uv:{pkg}",
                    Status.WARN,
                    Severity.RECOMMENDED,
                    category,
                    "not installed",
                    hint,
                )
            )

    return results


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------

STATUS_ICON = {
    Status.OK: "[green]✓[/]",
    Status.WARN: "[yellow]![/]",
    Status.ERROR: "[red]✗[/]",
}

SEVERITY_STYLE = {
    Severity.REQUIRED: "bold red",
    Severity.RECOMMENDED: "yellow",
    Severity.OPTIONAL: "dim",
}


def render_report(results: list[CheckResult], console: Console) -> int:
    """Print grouped tables and summary. Returns exit code."""
    # Group by category preserving insertion order
    groups: dict[str, list[CheckResult]] = {}
    for r in results:
        groups.setdefault(r.category, []).append(r)

    for category, checks in groups.items():
        table = Table(
            title=category, title_style="bold cyan", show_lines=False, pad_edge=False
        )
        table.add_column("", width=3, justify="center")  # status icon
        table.add_column("Check", min_width=25)
        table.add_column("Severity", width=12)
        table.add_column("Message")
        table.add_column("Fix Hint", style="dim")

        for c in checks:
            icon = STATUS_ICON[c.status]
            sev_style = SEVERITY_STYLE[c.severity]
            table.add_row(
                icon,
                c.name,
                f"[{sev_style}]{c.severity.value}[/]",
                c.message,
                c.fix_hint,
            )
        console.print(table)
        console.print()

    # Summary
    total = len(results)
    ok = sum(1 for r in results if r.status == Status.OK)
    warn = sum(1 for r in results if r.status == Status.WARN)
    error = sum(1 for r in results if r.status == Status.ERROR)
    required_failures = [
        r
        for r in results
        if r.status == Status.ERROR and r.severity == Severity.REQUIRED
    ]

    summary_lines = [
        f"[bold]Total:[/] {total}   [green]OK:[/] {ok}   [yellow]Warn:[/] {warn}   [red]Error:[/] {error}",
    ]

    if required_failures:
        summary_lines.append("")
        summary_lines.append("[bold red]REQUIRED checks failed — fix these first:[/]")
        for r in required_failures:
            hint = f"  → {r.fix_hint}" if r.fix_hint else ""
            summary_lines.append(f"  [red]✗[/] {r.name}: {r.message}{hint}")

    if warn and not required_failures:
        summary_lines.append("")
        summary_lines.append(
            "[yellow]Some recommended tools are missing. Run 'make install' (or 'make macos-arm64') to install them.[/]"
        )

    if not required_failures and not warn:
        summary_lines.append("")
        summary_lines.append(
            "[bold green]All checks passed! Your environment is ready.[/]"
        )

    border_style = "red" if required_failures else ("yellow" if warn else "green")
    console.print(
        Panel("\n".join(summary_lines), title="Summary", border_style=border_style)
    )

    return 1 if required_failures else 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def build_checks(repo: Path) -> list[CheckResult]:
    """Run all check functions and return combined results."""
    results: list[CheckResult] = []
    results.extend(check_versions(repo))
    results.extend(check_source_files(repo))
    results.extend(check_target_dirs())
    results.extend(check_core_binaries())
    results.extend(check_package_managers())
    results.extend(check_formatters())
    results.extend(check_linters())
    results.extend(check_config_files())
    results.extend(check_mason_packages())
    results.extend(check_python_packages())
    return results


def main() -> int:
    console = Console()
    plat = platform.system()
    arch = _arch()
    console.print(f"[bold]lunarvim-config doctor[/]  —  {plat} {arch}\n")

    repo = _repo_root()
    results = build_checks(repo)
    return render_report(results, console)


if __name__ == "__main__":
    sys.exit(main())
