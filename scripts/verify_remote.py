#!/usr/bin/env python3
"""
Verify a successful push by comparing local HEAD to origin/main and checking
that key files (README, LICENSE, .gitignore) exist on the remote.

Works on macOS and Windows. Standard library only.

Usage:
  python3 verify_remote.py <project-path>
  python3 verify_remote.py <project-path> --open
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import webbrowser
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


def run_git(args: list[str], cwd: Path) -> tuple[int, str, str]:
    try:
        r = subprocess.run(
            ["git"] + args,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=15,
        )
        return r.returncode, r.stdout, r.stderr
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return -1, "", str(e)


def get_remote_url(cwd: Path) -> str | None:
    code, out, _ = run_git(["remote", "get-url", "origin"], cwd)
    if code != 0:
        return None
    return out.strip() or None


def remote_url_to_html(url: str) -> str | None:
    """Convert git remote URL (SSH or HTTPS) to a github.com HTML URL."""
    url = url.strip()
    if url.startswith("git@github.com:"):
        path = url[len("git@github.com:"):]
        if path.endswith(".git"):
            path = path[:-4]
        return f"https://github.com/{path}"
    if url.startswith("https://github.com/"):
        if url.endswith(".git"):
            url = url[:-4]
        return url
    return None


def get_local_head(cwd: Path) -> str | None:
    code, out, _ = run_git(["rev-parse", "HEAD"], cwd)
    if code != 0:
        return None
    return out.strip()


def fetch_origin(cwd: Path) -> bool:
    code, _, _ = run_git(["fetch", "origin", "--quiet"], cwd)
    return code == 0


def get_remote_head(cwd: Path, branch: str = "main") -> str | None:
    code, out, _ = run_git(["rev-parse", f"origin/{branch}"], cwd)
    if code != 0:
        return None
    return out.strip()


def list_remote_files(cwd: Path, branch: str = "main") -> list[str]:
    code, out, _ = run_git(["ls-tree", "-r", "--name-only", f"origin/{branch}"], cwd)
    if code != 0:
        return []
    return [line for line in out.splitlines() if line]


def main() -> int:
    _require_git_or_exit()
    parser = argparse.ArgumentParser(description="Verify a successful push.")
    parser.add_argument("path", help="Project root path")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--open", action="store_true", help="Open the remote URL in a browser if verification succeeds")
    parser.add_argument("--format", choices=["json", "human"], default="human")
    args = parser.parse_args()

    cwd = Path(args.path).expanduser().resolve()
    if not cwd.exists() or not cwd.is_dir():
        print(f"error: {cwd} is not a directory", file=sys.stderr)
        return 1

    remote_url = get_remote_url(cwd)
    if not remote_url:
        result = {"ok": False, "error": "no 'origin' remote configured"}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    html_url = remote_url_to_html(remote_url)

    # Fetch
    if not fetch_origin(cwd):
        result = {
            "ok": False,
            "error": "could not git fetch origin",
            "remote_url": remote_url,
            "html_url": html_url,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    local_head = get_local_head(cwd)
    remote_head = get_remote_head(cwd, args.branch)
    heads_match = (local_head is not None) and (local_head == remote_head)

    remote_files = list_remote_files(cwd, args.branch)
    key_files = {"README.md", "LICENSE", ".gitignore"}
    present_key = sorted(f for f in remote_files if f in key_files)
    missing_key = sorted(key_files - set(remote_files))

    result: dict[str, Any] = {
        "ok": heads_match and not missing_key,
        "remote_url": remote_url,
        "html_url": html_url,
        "branch": args.branch,
        "local_head": local_head,
        "remote_head": remote_head,
        "heads_match": heads_match,
        "remote_file_count": len(remote_files),
        "key_files_present": present_key,
        "key_files_missing": missing_key,
    }

    if args.format == "human":
        print(f"Remote URL: {remote_url}")
        if html_url:
            print(f"Browse:     {html_url}")
        print(f"Branch:     {args.branch}")
        print(f"HEAD match: {'yes' if heads_match else 'NO (local != remote)'}")
        print(f"Remote files: {len(remote_files)}")
        print(f"Key files present: {', '.join(present_key) or '(none)'}")
        if missing_key:
            print(f"Key files MISSING: {', '.join(missing_key)}")
        print()
        print(f"Result: {'OK' if result['ok'] else 'FAIL'}")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))

    if result["ok"] and args.open and html_url:
        try:
            webbrowser.open(html_url)
        except Exception:
            pass

    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
