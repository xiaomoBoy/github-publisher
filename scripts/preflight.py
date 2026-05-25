#!/usr/bin/env python3
"""
Preflight check for github-publisher.

Verifies the local environment is ready to publish to GitHub. Reports each
check with a status and (if missing) an install command per OS, so the
calling AI assistant can offer to install the missing piece.

Checks:
  - python3 version
  - git installed + git config user.name/user.email
  - gh CLI installed (optional but preferred)
  - gh auth status (if gh present)
  - git credential.helper (so Path B can fetch a PAT)
  - network reachability of api.github.com
  - at least one usable GitHub auth path (A=gh / B=credential / C=manual)

Outputs human-readable text by default. Use --format json to get a machine-
readable summary for the orchestrator (publish.py / Claude).

Exit codes:
  0 = ready to publish (at least one auth path available)
  1 = missing required tools (e.g. git not installed)
  2 = ready with warnings (no gh, will fall back to credential or manual)

Stdlib only. Works on macOS and Windows.
"""
from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from typing import Any


def detect_os() -> str:
    sysname = platform.system().lower()
    if sysname == "darwin":
        return "macOS"
    if sysname == "windows":
        return "Windows"
    if sysname == "linux":
        return "Linux"
    return sysname


CURRENT_OS = detect_os()


def install_for(macos: str, windows: str, manual_url: str = "") -> dict[str, Any]:
    """Build a fix-block with install commands per OS."""
    return {
        "macOS": macos,
        "Windows": windows,
        "current_os_cmd": {"macOS": macos, "Windows": windows}.get(CURRENT_OS, ""),
        "manual_url": manual_url,
    }


def check_python() -> dict[str, Any]:
    v = sys.version_info
    ok = v.major == 3 and v.minor >= 8
    return {
        "name": "python3",
        "required": True,
        "status": "ok" if ok else "missing",
        "details": f"Python {v.major}.{v.minor}.{v.micro}",
        "fix": None if ok else install_for(
            macos="brew install python@3.11",
            windows="winget install --id Python.Python.3.11",
        ),
    }


def check_git() -> dict[str, Any]:
    if shutil.which("git") is None:
        return {
            "name": "git",
            "required": True,
            "status": "missing",
            "details": "git is not installed or not on PATH.",
            "fix": install_for(
                macos="brew install git",
                windows="winget install --id Git.Git",
                manual_url="https://git-scm.com/downloads",
            ),
        }
    try:
        r = subprocess.run(
            ["git", "--version"], capture_output=True, text=True, timeout=5,
        )
        return {
            "name": "git",
            "required": True,
            "status": "ok",
            "details": (r.stdout or r.stderr).strip(),
            "fix": None,
        }
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return {
            "name": "git",
            "required": True,
            "status": "missing",
            "details": f"git on PATH but cannot execute: {e}",
            "fix": install_for(
                macos="brew install git",
                windows="winget install --id Git.Git",
            ),
        }


def get_git_config(key: str) -> str | None:
    try:
        r = subprocess.run(
            ["git", "config", "--global", "--get", key],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    return None


def check_git_config_name() -> dict[str, Any]:
    name = get_git_config("user.name")
    if name:
        return {"name": "git.user.name", "required": True, "status": "ok", "details": name, "fix": None}
    return {
        "name": "git.user.name",
        "required": True,
        "status": "needs_setup",
        "details": "git config user.name is not set globally; commits will be rejected.",
        "fix": {
            "macOS": 'git config --global user.name "Your Name"',
            "Windows": 'git config --global user.name "Your Name"',
            "current_os_cmd": 'git config --global user.name "Your Name"',
            "manual_url": "",
            "interactive": True,
        },
    }


PERSONAL_EMAIL_DOMAINS = {
    "gmail.com", "googlemail.com",
    "outlook.com", "hotmail.com", "live.com",
    "yahoo.com", "yahoo.co.jp",
    "icloud.com", "me.com", "mac.com",
    "qq.com", "163.com", "126.com", "sina.com", "sina.cn",
    "foxmail.com", "yeah.net",
    "protonmail.com", "proton.me",
    "aol.com", "mail.com",
}


def _is_personal_email(email: str) -> bool:
    if "@" not in email:
        return False
    domain = email.split("@", 1)[1].lower()
    return domain in PERSONAL_EMAIL_DOMAINS


def check_git_config_email() -> dict[str, Any]:
    email = get_git_config("user.email")
    if email:
        # Personal email is still OK to commit with, but warn it will be public.
        # noreply alias users are fine, custom domains are fine.
        if _is_personal_email(email):
            return {
                "name": "git.user.email",
                "required": True,
                "status": "ok",
                "details": f"{email}  (heads up: personal email — every commit will publicly show it. To hide, see INSTALL.md § email privacy)",
                "fix": None,
            }
        return {"name": "git.user.email", "required": True, "status": "ok", "details": email, "fix": None}
    return {
        "name": "git.user.email",
        "required": True,
        "status": "needs_setup",
        "details": "git config user.email is not set globally; commits will be rejected.",
        "fix": {
            "macOS": 'git config --global user.email "you@example.com"',
            "Windows": 'git config --global user.email "you@example.com"',
            "current_os_cmd": 'git config --global user.email "you@example.com"',
            "manual_url": "https://github.com/settings/emails",
            "interactive": True,
            "tip": "Use <username>@users.noreply.github.com to keep your real email private.",
        },
    }


def check_gh_cli() -> dict[str, Any]:
    if shutil.which("gh") is None:
        return {
            "name": "gh",
            "required": False,
            "status": "warning",
            "details": "gh CLI is not installed. Not required — will fall back to API (Path B) or manual (Path C).",
            "fix": install_for(
                macos="brew install gh",
                windows="winget install --id GitHub.cli",
                manual_url="https://cli.github.com/",
            ),
        }
    try:
        r = subprocess.run(
            ["gh", "--version"], capture_output=True, text=True, timeout=5,
        )
        return {
            "name": "gh",
            "required": False,
            "status": "ok",
            "details": (r.stdout or "").splitlines()[0].strip(),
            "fix": None,
        }
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return {
            "name": "gh",
            "required": False,
            "status": "warning",
            "details": "gh on PATH but cannot execute",
            "fix": install_for(
                macos="brew install gh",
                windows="winget install --id GitHub.cli",
            ),
        }


def check_gh_auth() -> dict[str, Any]:
    if shutil.which("gh") is None:
        return {
            "name": "gh.auth",
            "required": False,
            "status": "warning",
            "details": "skipped (gh not installed)",
            "fix": None,
        }
    try:
        r = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True, text=True, timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return {
            "name": "gh.auth",
            "required": False,
            "status": "warning",
            "details": "gh auth status failed to run",
            "fix": None,
        }
    # gh auth status writes to stderr on success in older versions
    output = (r.stdout + "\n" + r.stderr).strip()
    if r.returncode == 0 and ("Logged in to github.com" in output or "Active account" in output):
        return {
            "name": "gh.auth",
            "required": False,
            "status": "ok",
            "details": output.splitlines()[0] if output else "logged in",
            "fix": None,
        }
    return {
        "name": "gh.auth",
        "required": False,
        "status": "warning",
        "details": "gh installed but not logged in (optional — only needed for Path A).",
        "fix": {
            "macOS": "gh auth login",
            "Windows": "gh auth login",
            "current_os_cmd": "gh auth login",
            "manual_url": "https://cli.github.com/manual/gh_auth_login",
            "interactive": True,
            "tip": "Interactive — opens browser. Choose: GitHub.com -> HTTPS -> Yes (cache) -> Login with browser.",
        },
    }


def check_git_credential() -> dict[str, Any]:
    """Try `git credential fill` for github.com. If it returns a password
    (PAT), Path B is available."""
    if shutil.which("git") is None:
        return {
            "name": "git.credential",
            "required": False,
            "status": "warning",
            "details": "skipped (git not installed)",
            "fix": None,
        }
    try:
        r = subprocess.run(
            ["git", "credential", "fill"],
            input="url=https://github.com\n\n",
            capture_output=True, text=True, timeout=8,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return {
            "name": "git.credential",
            "required": False,
            "status": "warning",
            "details": "git credential fill failed",
            "fix": None,
        }
    has_pw = any(line.startswith("password=") for line in r.stdout.splitlines())
    if has_pw:
        helper = get_git_config("credential.helper") or "(unspecified)"
        return {
            "name": "git.credential",
            "required": False,
            "status": "ok",
            "details": f"PAT available via credential helper: {helper}",
            "fix": None,
        }
    return {
        "name": "git.credential",
        "required": False,
        "status": "warning",
        "details": "No PAT cached for github.com. Path B (API) will not work; only Path A (gh) or Path C (manual) will.",
        "fix": {
            "macOS": "Either run `gh auth login` (recommended) OR create a PAT at https://github.com/settings/tokens/new (scope: repo) and let git remember it on first push.",
            "Windows": "Either run `gh auth login` (recommended) OR create a PAT at https://github.com/settings/tokens/new (scope: repo) and let git remember it on first push.",
            "current_os_cmd": "",
            "manual_url": "https://github.com/settings/tokens/new",
            "interactive": True,
        },
    }


def check_network() -> dict[str, Any]:
    try:
        req = urllib.request.Request(
            "https://api.github.com/zen",
            headers={"User-Agent": "github-publisher-preflight/0.1"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            ok = resp.status == 200
        return {
            "name": "network.github",
            "required": True,
            "status": "ok" if ok else "warning",
            "details": f"api.github.com HTTP {resp.status}",
            "fix": None,
        }
    except urllib.error.HTTPError as e:
        return {
            "name": "network.github",
            "required": True,
            "status": "warning",
            "details": f"api.github.com HTTP {e.code}",
            "fix": None,
        }
    except (urllib.error.URLError, TimeoutError) as e:
        return {
            "name": "network.github",
            "required": True,
            "status": "missing",
            "details": f"cannot reach api.github.com: {e}",
            "fix": {
                "macOS": "Check network / VPN / proxy. If using a proxy:\n  git config --global http.proxy http://127.0.0.1:7890",
                "Windows": "Check network / VPN / proxy. If using a proxy:\n  git config --global http.proxy http://127.0.0.1:7890",
                "current_os_cmd": "",
                "manual_url": "",
                "interactive": True,
            },
        }


def summarize(checks: list[dict[str, Any]]) -> dict[str, Any]:
    """Decide overall status + which auth paths are available."""
    by_name = {c["name"]: c for c in checks}

    # Required checks are tagged via the `required` field on each check.
    required = [c["name"] for c in checks if c.get("required")]
    missing_required = [
        name for name in required
        if by_name.get(name, {}).get("status") in ("missing", "needs_setup")
    ]

    # Auth paths
    path_a = by_name.get("gh.auth", {}).get("status") == "ok"
    path_b = by_name.get("git.credential", {}).get("status") == "ok"
    path_c = True  # manual is always available

    available_paths: list[str] = []
    if path_a:
        available_paths.append("A (gh CLI)")
    if path_b:
        available_paths.append("B (API via git credential)")
    available_paths.append("C (manual web walkthrough)")

    if missing_required:
        overall = "not_ready"
    elif not (path_a or path_b):
        overall = "ready_with_warnings"  # only manual available
    else:
        overall = "ready"

    return {
        "overall": overall,
        "missing_required": missing_required,
        "available_auth_paths": available_paths,
        "current_os": CURRENT_OS,
    }


def format_human(checks: list[dict[str, Any]], summary: dict[str, Any]) -> str:
    # Icon depends on (required, status): required+bad is loud, optional+bad is low-key.
    def icon_for(c: dict[str, Any]) -> str:
        status = c.get("status")
        required = c.get("required", False)
        if status == "ok":
            return "[OK]"
        if required:
            return "[X ]" if status == "missing" else "[!!]"
        return "[~ ]"  # optional, any non-ok state

    lines = []
    lines.append(f"=== Preflight ({CURRENT_OS}) ===")
    lines.append("")
    for c in checks:
        suffix = "" if c.get("required") else "  (optional)"
        lines.append(f"  {icon_for(c)} {c['name']:22s}  {c['details']}{suffix}")
    lines.append("")

    if summary["missing_required"]:
        lines.append("Required items missing — must fix before publishing:")
        for name in summary["missing_required"]:
            c = next((x for x in checks if x["name"] == name), None)
            if c and c.get("fix"):
                cmd = c["fix"].get("current_os_cmd") or c["fix"].get(CURRENT_OS, "")
                if cmd:
                    lines.append(f"  - {name}:  {cmd}")
                elif c["fix"].get("manual_url"):
                    lines.append(f"  - {name}:  see {c['fix']['manual_url']}")
        lines.append("")

    # Warnings (not blocking)
    warnings = [c for c in checks if c["status"] == "warning" and c.get("fix")]
    if warnings:
        lines.append("Optional improvements (publish will still work):")
        for c in warnings:
            cmd = c["fix"].get("current_os_cmd") or ""
            if cmd:
                lines.append(f"  - {c['name']}:  {cmd}")
        lines.append("")

    lines.append(f"Available auth paths: {', '.join(summary['available_auth_paths'])}")
    lines.append("")

    if summary["overall"] == "ready":
        lines.append("Ready to publish. You can ask the AI: 'open source this project'.")
    elif summary["overall"] == "ready_with_warnings":
        lines.append("Ready, but only the manual path (C) is available. Recommend installing gh or caching a PAT for a smoother flow.")
    else:
        lines.append("Not ready. Fix the items above and re-run preflight.")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Preflight check for github-publisher.")
    parser.add_argument("--format", choices=["human", "json"], default="human")
    args = parser.parse_args()

    checks = [
        check_python(),
        check_git(),
        check_git_config_name(),
        check_git_config_email(),
        check_gh_cli(),
        check_gh_auth(),
        check_git_credential(),
        check_network(),
    ]
    summary = summarize(checks)
    result = {"checks": checks, "summary": summary}

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_human(checks, summary))

    return {"ready": 0, "not_ready": 1, "ready_with_warnings": 2}[summary["overall"]]


if __name__ == "__main__":
    raise SystemExit(main())
