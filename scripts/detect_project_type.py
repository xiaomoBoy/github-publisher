#!/usr/bin/env python3
"""
Detect project type by looking at manifest files and file extensions.

Returns one of: python, node, shell, docs, claude-skill, mixed, unknown

Also reports:
  - file count, total size
  - whether git is initialized
  - detected fork (re-uses logic from scan_project but simpler)

Works on macOS and Windows. Standard library only.

Usage:
  python3 detect_project_type.py <project-path>
"""
from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

# Same skip set as scan_project.py
SKIP_DIRS = {
    ".git", "node_modules", "venv", ".venv", "env",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "dist", "build", ".next", ".nuxt", ".cache",
    "target", ".idea", ".vscode",
}

# Manifest -> project type
MANIFEST_TYPES: list[tuple[str, str]] = [
    ("pyproject.toml", "python"),
    ("setup.py", "python"),
    ("setup.cfg", "python"),
    ("requirements.txt", "python"),
    ("Pipfile", "python"),
    ("package.json", "node"),
    ("tsconfig.json", "node"),
    ("Cargo.toml", "rust"),
    ("go.mod", "go"),
    ("Gemfile", "ruby"),
    ("composer.json", "php"),
    ("mix.exs", "elixir"),
    ("pom.xml", "java"),
    ("build.gradle", "java"),
    ("build.gradle.kts", "java"),
]

CLAUDE_SKILL_MARKER = "SKILL.md"

EXTENSION_TYPES: dict[str, str] = {
    ".py": "python",
    ".js": "node",
    ".jsx": "node",
    ".ts": "node",
    ".tsx": "node",
    ".mjs": "node",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".fish": "shell",
    ".rs": "rust",
    ".go": "go",
    ".rb": "ruby",
    ".java": "java",
    ".kt": "java",
    ".php": "php",
    ".ex": "elixir",
    ".exs": "elixir",
}

DOCS_EXTENSIONS = {".md", ".rst", ".txt", ".mdx"}


def iter_files(root: Path) -> list[Path]:
    out: list[Path] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        out.append(p)
    return out


def detect_type(root: Path, files: list[Path]) -> tuple[str, list[str]]:
    """Return (primary_type, all_signals)."""
    signals: list[str] = []

    # 1. Manifest files
    for manifest, ptype in MANIFEST_TYPES:
        if (root / manifest).exists():
            signals.append(f"{ptype} (found {manifest})")

    # 2. Claude skill marker
    if (root / CLAUDE_SKILL_MARKER).exists():
        signals.append(f"claude-skill (found {CLAUDE_SKILL_MARKER} at root)")
    # also detect sub-skill collections
    has_subskill = any(
        p.name == CLAUDE_SKILL_MARKER and p.parent != root
        for p in files
    )
    if has_subskill:
        signals.append(f"claude-skill-collection (found {CLAUDE_SKILL_MARKER} in sub-dirs)")

    # 3. Extension counts
    ext_counter: Counter[str] = Counter()
    for p in files:
        ext = p.suffix.lower()
        if ext in EXTENSION_TYPES:
            ext_counter[EXTENSION_TYPES[ext]] += 1
        elif ext in DOCS_EXTENSIONS:
            ext_counter["docs"] += 1
        else:
            ext_counter["other"] += 1

    total_code_files = sum(v for k, v in ext_counter.items() if k != "other" and k != "docs")
    if total_code_files > 0:
        ext_summary = ", ".join(f"{k}:{v}" for k, v in ext_counter.most_common())
        signals.append(f"by extension: {ext_summary}")

    # Decide primary type
    # Priority: claude-skill > manifest type > dominant extension > docs > unknown
    if any("claude-skill" in s for s in signals):
        return "claude-skill", signals

    # Manifest match wins if extension agrees or there's no extension competition
    manifest_types = [s.split(" ")[0] for s in signals if "(found " in s]
    if manifest_types:
        primary = manifest_types[0]
        return primary, signals

    # Otherwise dominant extension
    code_only = {k: v for k, v in ext_counter.items() if k not in ("other", "docs")}
    if code_only:
        primary = max(code_only.items(), key=lambda kv: kv[1])[0]
        # if no clear winner, call it mixed
        sorted_counts = sorted(code_only.values(), reverse=True)
        if len(sorted_counts) > 1 and sorted_counts[0] < sorted_counts[1] * 2:
            return "mixed", signals
        return primary, signals

    # Mostly docs?
    if ext_counter.get("docs", 0) > ext_counter.get("other", 0):
        return "docs", signals

    return "unknown", signals


def get_total_size(files: list[Path]) -> int:
    total = 0
    for p in files:
        try:
            total += p.stat().st_size
        except OSError:
            pass
    return total


def check_git(root: Path) -> dict[str, Any]:
    info: dict[str, Any] = {"is_git_repo": (root / ".git").exists()}
    if not info["is_git_repo"]:
        return info

    try:
        remotes = subprocess.run(
            ["git", "remote", "-v"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=5,
        )
        remote_lines = remotes.stdout.strip().splitlines() if remotes.returncode == 0 else []
        info["remotes"] = [
            {"name": line.split()[0], "url": line.split()[1]}
            for line in remote_lines
            if len(line.split()) >= 2 and "(fetch)" in line
        ]
        info["has_upstream"] = any(r["name"] == "upstream" for r in info["remotes"])
    except (FileNotFoundError, subprocess.TimeoutExpired):
        info["remotes"] = []
        info["has_upstream"] = False

    return info


def detect_current_os() -> str:
    system = platform.system().lower()
    if system == "darwin":
        return "macOS"
    if system == "windows":
        return "Windows"
    if system == "linux":
        return "Linux"
    return system


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect project type for github-publisher.")
    parser.add_argument("path", help="Project root path")
    parser.add_argument("--format", choices=["json", "human"], default="human")
    args = parser.parse_args()

    root = Path(args.path).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 1

    files = iter_files(root)
    project_type, signals = detect_type(root, files)
    total_size = get_total_size(files)
    git_info = check_git(root)

    result = {
        "root": str(root),
        "project_type": project_type,
        "signals": signals,
        "file_count": len(files),
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / 1024 / 1024, 2),
        "git": git_info,
        "current_os": detect_current_os(),
    }

    if args.format == "human":
        print(f"Project root: {result['root']}")
        print(f"Project type: {result['project_type']}")
        print(f"Signals:")
        for s in signals:
            print(f"  - {s}")
        print(f"Files: {result['file_count']}  Size: {result['total_size_mb']} MB")
        print(f"Git: {'initialized' if git_info['is_git_repo'] else 'not initialized'}")
        if git_info.get("remotes"):
            for r in git_info["remotes"]:
                print(f"  remote {r['name']}: {r['url']}")
        if git_info.get("has_upstream"):
            print("  -> looks like a fork (has upstream remote)")
        print(f"Current OS: {result['current_os']}")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
