#!/usr/bin/env python3
"""Install the agent-tools toolbox into a target project.

This is the second half of project setup (the first half is
``scripts/project/bootstrap.sh``, which installs ``just`` and
validates ``git`` / ``gh``). ``init`` reads ``agent-tools.yaml``,
copies the agent-facing memory (``AGENT.md`` + ``.agent/skills/``)
into a target project root, and validates the environment so an
agent dropped into that project inherits the operational memory
instead of re-deriving it.

Usage:
    python3 scripts/project/init.py --target /path/to/project
                                    [--config agent-tools.yaml]
                                    [--mode copy|symlink]
                                    [--force]

No third-party deps: a tiny purpose-built parser handles the small,
flat ``agent-tools.yaml`` we control (install / validate sections).
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Keys we read out of agent-tools.yaml. We do NOT pull in PyYAML so the
# toolbox stays "clone and use" with zero pip installs; the config is a
# small flat file we own, so a minimal line scanner is sufficient and
# auditable.
DEFAULT_COPY_TARGETS = ["AGENT.md", ".agent/skills/"]
DEFAULT_VALIDATE = ["git", "gh", "gh_auth"]


def _read_install_section(config_path: Path) -> tuple[list[str], list[str]]:
    """Extract install.copy_into_target + install.validate lists.

    Falls back to defaults when the section is absent so init still
    works against the shipped minimal config.
    """
    copy_targets: list[str] = []
    validate: list[str] = []
    if not config_path.is_file():
        return DEFAULT_COPY_TARGETS, DEFAULT_VALIDATE

    section: str | None = None
    sub: str | None = None
    for raw in config_path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        stripped = line.strip()
        indent = len(line) - len(line.lstrip())
        if indent == 0 and stripped.endswith(":"):
            section = stripped[:-1]
            sub = None
            continue
        if section == "install":
            if indent == 2 and stripped.endswith(":"):
                sub = stripped[:-1]
                continue
            if indent >= 4 and stripped.startswith("- "):
                item = stripped[2:].strip().strip('"').strip("'")
                if sub == "copy_into_target":
                    copy_targets.append(item)
                elif sub == "validate":
                    validate.append(item)
    return (copy_targets or DEFAULT_COPY_TARGETS, validate or DEFAULT_VALIDATE)


def _validate_env(checks: list[str]) -> list[str]:
    problems: list[str] = []
    for check in checks:
        if check == "git" and shutil.which("git") is None:
            problems.append("git not found on PATH")
        elif check == "gh" and shutil.which("gh") is None:
            problems.append("gh (GitHub CLI) not found on PATH")
        elif check == "gh_auth":
            if shutil.which("gh") is None:
                problems.append("gh_auth: gh not installed")
            else:
                rc = subprocess.run(
                    ["gh", "auth", "status"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                ).returncode
                if rc != 0:
                    problems.append("gh auth status failed (run: gh auth login)")
    return problems


def _install_one(src: Path, dst: Path, mode: str, force: bool) -> str:
    if dst.exists() or dst.is_symlink():
        if not force:
            return f"skip (exists, use --force): {dst}"
        if dst.is_dir() and not dst.is_symlink():
            shutil.rmtree(dst)
        else:
            dst.unlink()
    dst.parent.mkdir(parents=True, exist_ok=True)
    if mode == "symlink":
        os.symlink(src, dst)
        return f"symlink: {dst} -> {src}"
    if src.is_dir():
        shutil.copytree(src, dst)
    else:
        shutil.copy2(src, dst)
    return f"copy: {dst}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Install agent-tools into a target project.")
    parser.add_argument("--target", required=True, help="Target project root.")
    parser.add_argument("--config", default=str(REPO_ROOT / "agent-tools.yaml"))
    parser.add_argument("--mode", choices=["copy", "symlink"], default="copy")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files.")
    args = parser.parse_args()

    target = Path(args.target).expanduser().resolve()
    if not target.is_dir():
        print(f"error: target is not a directory: {target}", file=sys.stderr)
        return 2

    copy_targets, validate = _read_install_section(Path(args.config).resolve())

    problems = _validate_env(validate)
    for line in (_install_one(REPO_ROOT / rel.rstrip("/"), target / rel.rstrip("/"), args.mode, args.force) for rel in copy_targets):
        print(line)

    if problems:
        print("--- environment warnings ---")
        for p in problems:
            print(f"  ! {p}")
        print("init completed with warnings (toolbox installed; fix the above before development).")
        return 1
    print("init ok — agent-tools installed into", target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
