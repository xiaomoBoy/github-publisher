#!/usr/bin/env python3
"""
Safely create a GitHub repository and push the local project.

Three fallback paths, tried in order:
  A. gh CLI is installed → `gh repo create`
  B. gh not available, but `git credential fill` returns a valid token →
     API call to /user/repos via urllib, token stays in a tempfile (never
     in env vars or stdout). Then git push over HTTPS (using same credential).
  C. Neither → print walkthrough instructions and exit with a code
     telling the caller to talk to the user.

Works on macOS and Windows. Standard library only.

Usage:
  python3 create_repo_safe.py <project-path> --name <repo-name> \\
      [--public | --private] [--description "..."] [--username <gh-user>]

Important: this script DOES create a remote repository. It is NOT idempotent
on the GitHub side. It also pushes to the new remote. Caller (the skill)
must confirm with the user before invoking.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
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


def have_command(name: str) -> bool:
    """True if command exists on PATH (handles .exe on Windows)."""
    return shutil.which(name) is not None


def get_existing_origin(cwd: Path) -> str | None:
    """Return the URL of the existing 'origin' remote, or None if not set."""
    try:
        r = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=str(cwd), capture_output=True, text=True, timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if r.returncode != 0:
        return None
    url = r.stdout.strip()
    return url or None


def fetch_credential_token(host: str = "github.com") -> str | None:
    """Use git credential fill to read a PAT for the given host.

    Returns the token (the 'password' field) on success, None on failure.
    The token is NOT logged. Caller must dispose of it carefully.
    """
    try:
        r = subprocess.run(
            ["git", "credential", "fill"],
            input=f"url=https://{host}\n\n",
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None

    if r.returncode != 0:
        return None

    for line in r.stdout.splitlines():
        if line.startswith("password="):
            return line.split("=", 1)[1]
    return None


def write_token_to_tempfile(token: str) -> Path:
    """Write the token to a 0600 tempfile and return its path."""
    fd, path_str = tempfile.mkstemp(prefix="ghp_", suffix=".tok")
    path = Path(path_str)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(token)
    except Exception:
        try:
            path.unlink()
        except OSError:
            pass
        raise
    # Best-effort restrictive perms (no-op on some Windows configs)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return path


def shred_file(path: Path) -> None:
    """Overwrite with random bytes then unlink. Best-effort, cross-platform."""
    try:
        size = path.stat().st_size
        with path.open("wb") as f:
            f.write(os.urandom(max(size, 64)))
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError:
                pass
    except OSError:
        pass
    try:
        path.unlink()
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Path A: gh CLI
# ---------------------------------------------------------------------------

def path_a_gh(
    *,
    cwd: Path,
    name: str,
    public: bool,
    description: str,
) -> dict[str, Any]:
    visibility_flag = "--public" if public else "--private"
    args = [
        "gh", "repo", "create", name,
        visibility_flag,
        "--source", str(cwd),
        "--remote", "origin",
        "--push",
    ]
    if description:
        args.extend(["--description", description])

    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=120)
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return {"ok": False, "path": "A", "error": str(e)}

    if r.returncode != 0:
        return {
            "ok": False, "path": "A",
            "error": (r.stderr or r.stdout).strip()[:500],
        }

    url = r.stdout.strip() or r.stderr.strip()
    return {"ok": True, "path": "A", "url": url, "method": "gh CLI"}


# ---------------------------------------------------------------------------
# Path B: API + git credential fill
# ---------------------------------------------------------------------------

def path_b_api(
    *,
    cwd: Path,
    name: str,
    public: bool,
    description: str,
    username_hint: str | None,
) -> dict[str, Any]:
    token = fetch_credential_token("github.com")
    if not token:
        return {"ok": False, "path": "B", "error": "no usable token from git credential fill"}

    token_path = write_token_to_tempfile(token)

    try:
        payload = json.dumps({
            "name": name,
            "description": description,
            "private": not public,
            "auto_init": False,
            "has_issues": True,
            "has_projects": False,
            "has_wiki": False,
        }).encode("utf-8")

        # Read token from file just at request build time
        token_str = token_path.read_text(encoding="utf-8")

        req = urllib.request.Request(
            "https://api.github.com/user/repos",
            data=payload,
            method="POST",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"token {token_str}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "github-publisher-skill/0.1",
                "Content-Type": "application/json",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace") if e.fp else ""
            return {
                "ok": False, "path": "B",
                "error": f"GitHub API HTTP {e.code}: {err_body[:300]}",
            }
        except urllib.error.URLError as e:
            return {"ok": False, "path": "B", "error": f"network error: {e}"}

        repo_info = json.loads(body)
        ssh_url = repo_info.get("ssh_url", "")
        https_url = repo_info.get("clone_url", "")
        html_url = repo_info.get("html_url", "")
        full_name = repo_info.get("full_name", "")

        # Now push. Try SSH first, fall back to HTTPS.
        remote_url = ssh_url or https_url
        if not remote_url:
            return {
                "ok": False, "path": "B",
                "error": "repo created but no clone URL returned",
            }

        # Check if origin already exists; set or add accordingly
        check = subprocess.run(
            ["git", "remote"], cwd=str(cwd), capture_output=True, text=True, timeout=10
        )
        existing_remotes = set((check.stdout or "").split())

        if "origin" in existing_remotes:
            subprocess.run(
                ["git", "remote", "set-url", "origin", remote_url],
                cwd=str(cwd), check=True, capture_output=True, text=True, timeout=10,
            )
        else:
            subprocess.run(
                ["git", "remote", "add", "origin", remote_url],
                cwd=str(cwd), check=True, capture_output=True, text=True, timeout=10,
            )

        # Push
        push = subprocess.run(
            ["git", "push", "-u", "origin", "main"],
            cwd=str(cwd), capture_output=True, text=True, timeout=120,
        )
        if push.returncode != 0:
            # If SSH push failed, try switching to HTTPS and retry
            if remote_url == ssh_url and https_url:
                subprocess.run(
                    ["git", "remote", "set-url", "origin", https_url],
                    cwd=str(cwd), check=True, capture_output=True, text=True, timeout=10,
                )
                push = subprocess.run(
                    ["git", "push", "-u", "origin", "main"],
                    cwd=str(cwd), capture_output=True, text=True, timeout=120,
                )

        if push.returncode != 0:
            return {
                "ok": False, "path": "B",
                "error": "repo created but git push failed",
                "stderr": (push.stderr or push.stdout).strip()[:500],
                "url": html_url,
                "hint": "Try `git push -u origin main` manually after configuring SSH or HTTPS auth.",
            }

        return {
            "ok": True, "path": "B",
            "url": html_url,
            "full_name": full_name,
            "method": "GitHub API + git push",
        }

    finally:
        shred_file(token_path)
        # nothing else holds the token string in this scope; let GC collect
        try:
            del token, token_str
        except NameError:
            pass


# ---------------------------------------------------------------------------
# Path C: manual walkthrough
# ---------------------------------------------------------------------------

def path_c_manual(*, name: str, public: bool, username_hint: str | None) -> dict[str, Any]:
    user = username_hint or "<your-username>"
    visibility = "Public" if public else "Private"
    instructions = f"""
No 'gh' command and no stored PAT for github.com — please create the repo manually:

1. Open https://github.com/new in your browser (must be logged in)

2. Fill in:
   - Repository name: {name}
   - Visibility: {visibility}
   - DO NOT check any of: Add README, Add .gitignore, Choose a license
     (we already generated these locally; ticking them will cause push conflicts)

3. Click 'Create repository'

4. The next page shows setup instructions. Look for the section titled
   '...or push an existing repository from the command line'. Copy the 3 lines:

   git remote add origin git@github.com:{user}/{name}.git
   git branch -M main
   git push -u origin main

5. Paste them in your terminal (inside the project directory) and run.

If 'git push' fails with 'Permission denied (publickey)', switch the remote
to HTTPS instead:

   git remote set-url origin https://github.com/{user}/{name}.git
   git push -u origin main

When HTTPS asks for a password, paste a GitHub Personal Access Token:
https://github.com/settings/tokens/new (scope: 'repo')

For more help, see references/github-no-gh-walkthrough.md and references/troubleshooting.md.
"""
    return {
        "ok": False,  # not done — needs human action
        "path": "C",
        "manual": True,
        "instructions": instructions.strip(),
    }


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def main() -> int:
    _require_git_or_exit()
    parser = argparse.ArgumentParser(description="Safely create a GitHub repo and push.")
    parser.add_argument("path", help="Project root path (must already be a git repo with a commit)")
    parser.add_argument("--name", required=True, help="Repository name (will be created under your user)")
    visibility = parser.add_mutually_exclusive_group()
    visibility.add_argument("--public", action="store_true", default=True)
    visibility.add_argument("--private", action="store_true")
    parser.add_argument("--description", default="", help="Repo description")
    parser.add_argument("--username", default=None, help="GitHub username hint (for path C instructions)")
    parser.add_argument("--prefer-path", choices=["auto", "A", "B", "C"], default="auto",
                        help="Force a specific path (default: auto = try A → B → C)")
    parser.add_argument(
        "--force-overwrite-origin",
        action="store_true",
        help="Overwrite an existing 'origin' remote without asking. Default: refuse.",
    )
    args = parser.parse_args()

    cwd = Path(args.path).expanduser().resolve()
    if not cwd.exists() or not cwd.is_dir():
        print(f"error: {cwd} is not a directory", file=sys.stderr)
        return 1
    if not (cwd / ".git").exists():
        print(f"error: {cwd} is not a git repository (run 'git init' first)", file=sys.stderr)
        return 1

    # Safety check: refuse to overwrite an existing 'origin' remote
    existing_origin = get_existing_origin(cwd)
    if existing_origin and not args.force_overwrite_origin:
        print(json.dumps({
            "ok": False,
            "error": (
                f"git remote 'origin' already exists and points to: {existing_origin}\n"
                f"Refusing to overwrite without explicit confirmation."
            ),
            "existing_origin": existing_origin,
            "hint": (
                "Choose one:\n"
                "  (a) If origin already points to the GitHub repo you want, you're done — "
                "just run `git push -u origin main` manually.\n"
                "  (b) If you really want to replace it, re-run with --force-overwrite-origin.\n"
                "  (c) Remove the existing remote first: `git remote remove origin`, then re-run."
            ),
        }, ensure_ascii=False, indent=2))
        return 4  # special exit code: refused due to existing origin

    is_public = not args.private  # public by default

    # Determine available paths
    available_a = have_command("gh")

    chosen_paths: list[str] = []
    if args.prefer_path != "auto":
        chosen_paths = [args.prefer_path]
    else:
        if available_a:
            chosen_paths.append("A")
        chosen_paths.append("B")  # always try API path as fallback
        chosen_paths.append("C")  # always have manual as last resort

    last_result: dict[str, Any] = {}
    for p in chosen_paths:
        if p == "A":
            if not available_a:
                last_result = {"ok": False, "path": "A", "error": "gh CLI not installed"}
                continue
            result = path_a_gh(
                cwd=cwd, name=args.name,
                public=is_public, description=args.description,
            )
        elif p == "B":
            result = path_b_api(
                cwd=cwd, name=args.name,
                public=is_public, description=args.description,
                username_hint=args.username,
            )
        else:  # C
            result = path_c_manual(
                name=args.name, public=is_public,
                username_hint=args.username,
            )

        last_result = result
        if result.get("ok"):
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0

        # If path B failed for "no token", try C
        if p == "B" and "no usable token" in (result.get("error") or ""):
            continue
        # If path A failed (gh issue), try B
        if p == "A":
            continue
        # If path C was reached, it means we need user action — exit specially
        if p == "C":
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 3  # special exit code: needs manual action

    print(json.dumps(last_result, ensure_ascii=False, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
