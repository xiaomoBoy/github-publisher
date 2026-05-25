#!/usr/bin/env python3
"""
Check the git config user.email for whether it looks like a personal email
that the user may not want exposed in commit history.

Reports a recommendation but does NOT change anything. The caller (the skill)
should ask the user whether to apply the suggested change.

Works on macOS and Windows. Standard library only.

Usage:
  python3 check_git_config.py <project-path>
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def _require_git_or_exit() -> None:
    """Exit with a clear message if git is not installed."""
    if shutil.which("git") is None:
        print("error: git is not installed or not on PATH.", file=sys.stderr)
        print("  Install instructions:", file=sys.stderr)
        print("    macOS:   brew install git", file=sys.stderr)
        print("    Windows: winget install --id Git.Git  (or download from https://git-scm.com)", file=sys.stderr)
        print("  After installing, re-run this command.", file=sys.stderr)
        sys.exit(2)

NOREPLY_PATTERN = re.compile(r"^[^@\s]+@users\.noreply\.github\.com$", re.IGNORECASE)
COMMON_PERSONAL_DOMAINS = {
    "gmail.com", "googlemail.com",
    "outlook.com", "hotmail.com", "live.com",
    "yahoo.com", "yahoo.co.jp",
    "icloud.com", "me.com", "mac.com",
    "qq.com", "163.com", "126.com", "sina.com", "sina.cn",
    "foxmail.com", "yeah.net",
    "protonmail.com", "proton.me",
    "aol.com",
    "mail.com",
}


def get_git_config(key: str, cwd: Path) -> str | None:
    try:
        # try local first
        r = subprocess.run(
            ["git", "config", "--get", key],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None

    # try global
    try:
        r = subprocess.run(
            ["git", "config", "--global", "--get", key],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None

    return None


def classify_email(email: str | None) -> dict[str, Any]:
    if not email:
        return {
            "status": "missing",
            "message": "No git user.email is configured. You must set one before you can commit.",
            "suggestion": 'git config user.email "your-email@example.com"',
        }

    if NOREPLY_PATTERN.match(email):
        return {
            "status": "noreply",
            "message": f"Email '{email}' is a GitHub noreply alias. Good — your real address stays private.",
            "suggestion": None,
        }

    domain = email.split("@", 1)[1].lower() if "@" in email else ""
    if domain in COMMON_PERSONAL_DOMAINS:
        return {
            "status": "personal",
            "message": f"Email '{email}' looks like a personal address. Every commit you push will publicly show it.",
            "suggestion": (
                "Consider switching to GitHub's noreply alias before committing. Find yours at "
                "https://github.com/settings/emails (the format is "
                "<id>+<username>@users.noreply.github.com or <username>@users.noreply.github.com). "
                "Set it for this repo only with:\n"
                "  git config user.email '<your-username>@users.noreply.github.com'\n"
                "or globally:\n"
                "  git config --global user.email '<your-username>@users.noreply.github.com'"
            ),
        }

    # Looks like a work / custom domain email
    return {
        "status": "custom",
        "message": f"Email '{email}' uses a custom domain. It will be publicly visible in every commit. If that's OK (e.g. your work email), no action needed.",
        "suggestion": None,
    }


def main() -> int:
    _require_git_or_exit()
    parser = argparse.ArgumentParser(description="Check git user.email for privacy risk.")
    parser.add_argument("path", help="Project root path")
    parser.add_argument("--format", choices=["json", "human"], default="human")
    args = parser.parse_args()

    root = Path(args.path).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 1

    name = get_git_config("user.name", root)
    email = get_git_config("user.email", root)
    classification = classify_email(email)

    result = {
        "user.name": name,
        "user.email": email,
        "classification": classification,
    }

    if args.format == "human":
        print(f"user.name:  {name or '(not set)'}")
        print(f"user.email: {email or '(not set)'}")
        print(f"Status: {classification['status']}")
        print(f"  {classification['message']}")
        if classification.get("suggestion"):
            print()
            print("Suggestion:")
            print(f"  {classification['suggestion']}")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))

    # exit codes: 0 ok, 1 personal email (recommend change), 2 missing
    code_map = {"noreply": 0, "custom": 0, "personal": 1, "missing": 2}
    return code_map.get(classification["status"], 0)


if __name__ == "__main__":
    raise SystemExit(main())
