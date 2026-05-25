#!/usr/bin/env python3
"""
One-command orchestrator for github-publisher.

Runs the full publish workflow phase by phase with sensible defaults, stopping
only at hard checkpoints (scan red / push confirmation / missing prerequisites).
The calling AI (Claude / Copilot / etc.) drives the interactive parts; this
script is non-interactive.

Phases:
  1. preflight                 -> exit 10 if missing required tools
  2. detect project type
  3. scan (private data / attribution / large files)
                               -> exit 11 if red
  4. generate README/LICENSE/.gitignore (using defaults + scan results)
  5. git init / commit (if needed)
  6. plan summary + push       -> exit 12 if --yes not passed (review-then-confirm)
  7. push via create_repo_safe -> exit 13 if repo creation falls back to manual
  8. verify_remote

Usage:
  python3 publish.py <project-path>
    [--name <repo-name>]              # default: dir basename, kebab-cased
    [--license MIT|Apache-2.0|GPL-3.0] # default: MIT
    [--public | --private]            # default: --public
    [--description "..."]             # default: empty
    [--author <gh-username>]          # default: from git config / GH user
    [--commit-message "..."]          # default: "Initial commit"
    [--yes]                           # confirm push (AI passes after user "y")
    [--skip-preflight]                # skip phase 1
    [--no-push]                       # do everything except phase 7 + 8
    [--format human|json]             # default: human

Exit codes:
  0  = success (all phases done, repo created and verified)
  1  = generic error
  10 = preflight failed (missing required tools)
  11 = scan returned RED (must fix and re-run)
  12 = ready to push, --yes not passed (review-then-confirm checkpoint)
  13 = push fell back to Path C (manual web walkthrough required)

Stdlib only. Works on macOS and Windows.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPTS_DIR.parent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_script(script: str, args: list[str]) -> tuple[int, str, str]:
    """Run another script in scripts/, capturing stdout/stderr."""
    cmd = [sys.executable, str(SCRIPTS_DIR / script)] + args
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired as e:
        return -1, "", f"timeout: {e}"
    except Exception as e:
        return -2, "", f"error: {e}"


def kebab(name: str) -> str:
    """Coerce a string to a GitHub-friendly kebab-case repo name."""
    s = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-._")
    return s or "my-project"


def git(args: list[str], cwd: Path) -> tuple[int, str, str]:
    try:
        r = subprocess.run(
            ["git"] + args, cwd=str(cwd),
            capture_output=True, text=True, timeout=30,
        )
        return r.returncode, r.stdout, r.stderr
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return -1, "", str(e)


def get_gh_username() -> str | None:
    """Try to learn the user's GitHub username from gh or git config."""
    # try gh first
    try:
        r = subprocess.run(
            ["gh", "api", "user", "--jq", ".login"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    # fall back to git config noreply email parse
    try:
        r = subprocess.run(
            ["git", "config", "--global", "--get", "user.email"],
            capture_output=True, text=True, timeout=5,
        )
        email = r.stdout.strip()
        m = re.match(r"^(?:\d+\+)?([A-Za-z0-9-]+)@users\.noreply\.github\.com$", email)
        if m:
            return m.group(1)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def header(title: str) -> str:
    return f"\n=== {title} ==="


# ---------------------------------------------------------------------------
# Phase runners
# ---------------------------------------------------------------------------

def phase_preflight(emit) -> dict[str, Any]:
    emit(header("Phase 1 — Preflight"))
    code, out, err = run_script("preflight.py", ["--format", "json"])
    if code == -1 or code == -2:
        emit(f"preflight failed to run: {err}")
        return {"ok": False, "exit": 10, "error": err}

    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        emit("could not parse preflight JSON")
        return {"ok": False, "exit": 10, "error": "preflight bad JSON"}

    summary = data["summary"]
    emit(f"Overall: {summary['overall']}")
    emit(f"Auth paths: {', '.join(summary['available_auth_paths'])}")
    for c in data["checks"]:
        if c["status"] in ("missing", "needs_setup"):
            emit(f"  [!] {c['name']}: {c['details']}")
            if c.get("fix"):
                cmd = c["fix"].get("current_os_cmd") or ""
                if cmd:
                    emit(f"      fix: {cmd}")

    if summary["overall"] == "not_ready":
        return {
            "ok": False, "exit": 10,
            "error": "preflight not ready",
            "missing_required": summary["missing_required"],
            "preflight": data,
        }
    return {"ok": True, "preflight": data}


def phase_detect(emit, project_path: Path) -> dict[str, Any]:
    emit(header("Phase 2 — Detect project"))
    code, out, err = run_script(
        "detect_project_type.py", [str(project_path), "--format", "json"],
    )
    if code != 0:
        emit(f"detect failed: {err}")
        return {"ok": False, "error": err}
    data = json.loads(out)
    emit(f"Type: {data['project_type']}")
    emit(f"Files: {data['file_count']}  Size: {data['total_size_mb']} MB")
    emit(f"Git: {'initialized' if data['git']['is_git_repo'] else 'not initialized'}")
    if data["git"].get("has_upstream"):
        emit("  (detected fork via upstream remote)")
    return {"ok": True, "detect": data}


def phase_scan(emit, project_path: Path, scan_output_path: Path) -> dict[str, Any]:
    emit(header("Phase 3 — Security + attribution scan"))
    code, out, err = run_script(
        "scan_project.py", [str(project_path), "--format", "json"],
    )
    if code < 0:
        emit(f"scan failed: {err}")
        return {"ok": False, "exit": 11, "error": err}

    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        emit("scan returned non-JSON")
        return {"ok": False, "exit": 11, "error": "bad JSON"}

    # Save scan output for generate phase
    scan_output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    s = data["summary"]
    emit(f"Status: {data['status'].upper()}")
    emit(
        f"Private paths: {s['private_paths']}  "
        f"Strong secrets: {s['strong_secrets']}  "
        f"Sensitive files: {s['sensitive_files']}  "
        f"Large files: {s['large_files']}"
    )
    if data["status"] == "red":
        emit("")
        emit("RED findings — must fix before publishing:")
        for f in data["private_findings"][:15]:
            if f.get("severity") != "red":
                continue
            loc = f"{f['file']}:{f['line']}" if f.get("line") else f["file"]
            emit(f"  - {f['category']}/{f['type']} @ {loc}")
            emit(f"      preview: {f['match_preview']}")
            emit(f"      fix:     {f['fix_hint']}")
        more = sum(1 for f in data["private_findings"] if f.get("severity") == "red") - 15
        if more > 0:
            emit(f"  ... and {more} more red findings")
        emit("")
        emit("After fixing, re-run: python3 publish.py <path> ...")
        return {"ok": False, "exit": 11, "scan": data}

    return {"ok": True, "scan": data}


def phase_generate(
    emit,
    project_path: Path,
    name: str,
    license_name: str,
    description: str,
    author: str,
    tested_on: str,
    project_type: str,
    scan_output_path: Path,
    install_cmd: str | None = None,
    usage_example: str | None = None,
    regenerate: bool = False,
) -> dict[str, Any]:
    emit(header("Phase 4 — Generate README / LICENSE / .gitignore"))
    extra: list[str] = []
    if install_cmd:
        extra.extend(["--install-cmd", install_cmd])
    if usage_example:
        extra.extend(["--usage-example", usage_example])
    if regenerate:
        extra.append("--force")
    code, out, err = run_script("generate_files.py", [
        str(project_path),
        "--license", license_name,
        "--type", project_type,
        "--name", name,
        "--description", description,
        "--author", author,
        "--tested-on", tested_on,
        "--scan-result", str(scan_output_path),
        *extra,
    ])
    if code != 0 and code != 1:
        emit(f"generate failed: {err or out}")
        return {"ok": False, "error": err or out}

    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        emit(f"generate returned non-JSON: {out[:200]}")
        return {"ok": False, "error": "bad JSON"}

    for r in data["results"]:
        prefix = "  [ok]  " if r["ok"] else "  [skip]"
        emit(f"{prefix} {r['file']}: {r['message']}")
    skipped = [r["file"] for r in data["results"] if not r["ok"]]
    if skipped and not regenerate:
        emit("  (To regenerate with current args, add --regenerate-docs.)")
    return {"ok": True, "generate": data}


def phase_git(emit, project_path: Path, commit_message: str) -> dict[str, Any]:
    emit(header("Phase 5 — Local git (init + commit)"))

    # init if needed
    if not (project_path / ".git").exists():
        emit("  git init -b main")
        code, _, err = git(["init", "-b", "main"], project_path)
        if code != 0:
            # older git without -b
            code, _, _ = git(["init"], project_path)
            if code == 0:
                git(["checkout", "-b", "main"], project_path)

    # check user.email softly (preflight already required it)
    code, out, _ = git(["config", "--get", "user.email"], project_path)
    if code == 0 and out.strip():
        email = out.strip()
        if email.endswith("@users.noreply.github.com"):
            emit(f"  email: {email} (noreply — good)")
        elif any(email.endswith(d) for d in (
            "@gmail.com", "@outlook.com", "@hotmail.com", "@yahoo.com",
            "@qq.com", "@163.com", "@126.com", "@icloud.com",
        )):
            emit(f"  email: {email}")
            emit("  NOTE: this is a personal email and will be public on every commit.")
            emit("        consider: git config user.email '<username>@users.noreply.github.com'")
        else:
            emit(f"  email: {email}")

    # stage
    git(["add", "-A"], project_path)

    # is there anything to commit?
    code, out, _ = git(["status", "--porcelain"], project_path)
    has_changes = bool(out.strip())

    # any prior commits?
    code_h, _, _ = git(["rev-parse", "HEAD"], project_path)
    has_history = (code_h == 0)

    if not has_changes and has_history:
        emit("  nothing new to commit (working tree clean)")
        return {"ok": True, "committed": False, "had_history": True}

    if not has_changes and not has_history:
        emit("  nothing to commit and no history; project is empty?")
        return {"ok": False, "error": "empty project, nothing to commit"}

    # do commit
    code, out, err = git(["commit", "-m", commit_message], project_path)
    if code != 0:
        emit(f"  git commit failed: {(err or out).strip()[:200]}")
        return {"ok": False, "error": "git commit failed"}

    emit(f"  committed: {commit_message}")
    return {"ok": True, "committed": True}


def phase_plan_summary(
    emit,
    project_path: Path,
    name: str,
    visibility: str,
    license_name: str,
    description: str,
    author: str,
) -> None:
    emit(header("Pre-push review (re-run with --yes to confirm)"))
    emit(f"  Project path:    {project_path}")
    emit(f"  Repo name:       {name}")
    emit(f"  Visibility:      {visibility}")
    emit(f"  License:         {license_name}")
    emit(f"  Description:     {description or '(none)'}")
    emit(f"  Author:          {author}")
    emit(f"  Will create:     https://github.com/{author}/{name}")
    emit("")
    emit("Once pushed, the contents are public on the internet. Cached by")
    emit("crawlers — even deleting the repo later does not guarantee removal.")
    emit("")
    emit("To proceed, re-run with --yes (the AI should ask the user first).")


def phase_create_and_push(
    emit,
    project_path: Path,
    name: str,
    public: bool,
    description: str,
    author: str | None,
) -> dict[str, Any]:
    emit(header("Phase 6 — Create GitHub repo + push"))
    args = [str(project_path), "--name", name]
    if public:
        args.append("--public")
    else:
        args.append("--private")
    if description:
        args.extend(["--description", description])
    if author:
        args.extend(["--username", author])

    code, out, err = run_script("create_repo_safe.py", args)
    out = out.strip()

    # create_repo_safe.py emits JSON
    data: dict[str, Any] = {}
    try:
        data = json.loads(out) if out else {}
    except json.JSONDecodeError:
        emit(out)
        emit(err.strip())

    if code == 0 and data.get("ok"):
        emit(f"  Created: {data.get('url', '(no url)')}")
        emit(f"  Method:  {data.get('method', '?')}")
        return {"ok": True, "create": data, "exit": 0}

    if code == 3:
        # path C — manual walkthrough required
        emit("  No auth available for automatic creation.")
        emit("  Please follow the manual walkthrough below:")
        emit("")
        emit(data.get("instructions", "(no instructions)"))
        return {"ok": False, "exit": 13, "create": data}

    if code == 4:
        # origin already exists
        emit(f"  Refused: {data.get('error', '')}")
        emit("")
        emit(data.get("hint", ""))
        return {"ok": False, "exit": 1, "create": data}

    emit(f"  create_repo_safe failed (exit {code}): {data.get('error', err.strip())[:300]}")
    return {"ok": False, "exit": 1, "create": data}


def phase_verify(emit, project_path: Path) -> dict[str, Any]:
    emit(header("Phase 7 — Verify remote"))
    code, out, err = run_script(
        "verify_remote.py", [str(project_path), "--format", "json"],
    )
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        emit(f"verify returned non-JSON: {out[:200]}")
        return {"ok": False, "error": "bad JSON"}

    emit(f"  Remote:  {data.get('remote_url', '?')}")
    emit(f"  Browse:  {data.get('html_url', '?')}")
    emit(f"  HEAD match: {data.get('heads_match')}")
    emit(f"  Remote files: {data.get('remote_file_count')}")
    emit(f"  Key files present: {', '.join(data.get('key_files_present') or []) or '(none)'}")
    missing = data.get("key_files_missing") or []
    if missing:
        emit(f"  Key files MISSING: {', '.join(missing)}")
    return {"ok": bool(data.get("ok")), "verify": data}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="One-command publish orchestrator.")
    parser.add_argument("path", help="Project root path")
    parser.add_argument("--name", default=None, help="Repo name (default: dir basename, kebab-cased)")
    parser.add_argument("--license", default="MIT", help="License (MIT / Apache-2.0 / GPL-3.0)")
    parser.add_argument("--type", default=None,
                        help="Override detected project type (python / node / shell / docs / general)")
    visibility = parser.add_mutually_exclusive_group()
    visibility.add_argument("--public", action="store_true")
    visibility.add_argument("--private", action="store_true")
    parser.add_argument("--description", default="")
    parser.add_argument("--author", default=None, help="GitHub username (default: auto-detected)")
    parser.add_argument("--commit-message", default="Initial commit")
    parser.add_argument("--install-cmd", default=None, help="Real install instructions for README")
    parser.add_argument("--usage-example", default=None, help="Real usage example for README")
    parser.add_argument("--regenerate-docs", action="store_true",
                        help="Overwrite existing README/LICENSE/.gitignore (default: skip if present)")
    parser.add_argument("--yes", action="store_true", help="Confirm push (AI passes after user 'y')")
    parser.add_argument("--dry-run", action="store_true",
                        help="Zero-side-effect preview: run preflight + detect + scan + print plan only. "
                             "No file writes, no git init, no commit.")
    parser.add_argument("--skip-preflight", action="store_true")
    parser.add_argument("--no-push", action="store_true", help="Run everything except create+push+verify")
    parser.add_argument("--format", choices=["human", "json"], default="human")
    args = parser.parse_args()

    project_path = Path(args.path).expanduser().resolve()
    if not project_path.exists() or not project_path.is_dir():
        print(f"error: {project_path} is not a directory", file=sys.stderr)
        return 1

    output_lines: list[str] = []

    def emit(s: str) -> None:
        output_lines.append(s)
        if args.format == "human":
            print(s)

    public = True if not args.private else False
    visibility_label = "Public" if public else "Private"
    license_name = args.license
    description = args.description
    name = args.name or kebab(project_path.name)
    author = args.author or get_gh_username() or "your-username"
    tested_on = "macOS and Windows"

    # Scan output goes to a tempfile so it doesn't pollute the project tree
    # (and so re-running publish.py doesn't trigger scan on its own output).
    scan_fd, scan_output_str = tempfile.mkstemp(prefix="ghpub_scan_", suffix=".json")
    import os as _os
    _os.close(scan_fd)
    scan_output_path = Path(scan_output_str)

    state: dict[str, Any] = {"name": name, "visibility": visibility_label, "license": license_name}

    # Phase 1
    if not args.skip_preflight:
        r = phase_preflight(emit)
        state["preflight"] = r
        if not r["ok"]:
            return _final(args.format, output_lines, state, r["exit"])

    # Phase 2
    r = phase_detect(emit, project_path)
    state["detect"] = r
    if not r["ok"]:
        return _final(args.format, output_lines, state, 1)
    project_type = r["detect"]["project_type"]
    # generate_files knows: python / node / shell / docs / claude-skill / general
    if args.type:
        gen_type = args.type
    elif project_type in ("python", "node", "shell", "docs", "claude-skill"):
        gen_type = project_type
    else:
        gen_type = "general"

    # Phase 3
    r = phase_scan(emit, project_path, scan_output_path)
    state["scan"] = r
    if not r["ok"]:
        return _final(args.format, output_lines, state, r.get("exit", 1))

    # --dry-run stops here, before any file writes or git changes
    if args.dry_run:
        emit(header("Dry-run preview (no files written, no git changes)"))
        emit(f"  Project path:    {project_path}")
        emit(f"  Repo name:       {name}")
        emit(f"  Visibility:      {visibility_label}")
        emit(f"  License:         {license_name}")
        emit(f"  Project type:    {gen_type}")
        emit(f"  Description:     {description or '(none)'}")
        emit(f"  Author:          {author}")
        emit(f"  Would create:    https://github.com/{author}/{name}")
        emit("")
        emit("Would do if you re-ran without --dry-run:")
        emit("  Phase 4: write LICENSE / README.md / .gitignore (skipping any that exist)")
        emit("  Phase 5: git init + git add -A + initial commit (skipping if already done)")
        emit("  Phase 6 (with --yes): create GitHub repo + push")
        emit("  Phase 7 (with --yes): verify remote")
        emit("")
        emit("To proceed for real:")
        emit(f"  python3 scripts/publish.py {args.path} [same args]            # stop at pre-push review")
        emit(f"  python3 scripts/publish.py {args.path} [same args] --yes      # push to GitHub")
        return _final(args.format, output_lines, state, 0)

    # Phase 4
    r = phase_generate(
        emit, project_path,
        name=name, license_name=license_name,
        description=description, author=author,
        tested_on=tested_on, project_type=gen_type,
        scan_output_path=scan_output_path,
        install_cmd=args.install_cmd,
        usage_example=args.usage_example,
        regenerate=args.regenerate_docs,
    )
    state["generate"] = r
    if not r["ok"]:
        return _final(args.format, output_lines, state, 1)

    # Phase 5
    r = phase_git(emit, project_path, args.commit_message)
    state["git"] = r
    if not r["ok"]:
        return _final(args.format, output_lines, state, 1)

    # Pre-push checkpoint
    if not args.yes:
        phase_plan_summary(
            emit, project_path, name, visibility_label,
            license_name, description, author,
        )
        return _final(args.format, output_lines, state, 12)

    if args.no_push:
        emit(header("--no-push set; stopping before Phase 6"))
        return _final(args.format, output_lines, state, 0)

    # Phase 6
    r = phase_create_and_push(
        emit, project_path, name=name, public=public,
        description=description, author=author,
    )
    state["create"] = r
    if not r["ok"]:
        return _final(args.format, output_lines, state, r.get("exit", 1))

    # Phase 7
    r = phase_verify(emit, project_path)
    state["verify"] = r

    # Cleanup scan tmp
    try:
        scan_output_path.unlink()
    except OSError:
        pass

    if r["ok"]:
        emit("")
        emit("Done. The project is live on GitHub.")
        repo_url = r["verify"].get("html_url") or f"https://github.com/{author}/{name}"

        # Warn if README still contains generator placeholders
        readme_path = project_path / "README.md"
        placeholder_hits: list[str] = []
        if readme_path.exists():
            try:
                readme_body = readme_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                readme_body = ""
            if "<install instructions go here>" in readme_body:
                placeholder_hits.append("install instructions")
            if "<usage example goes here>" in readme_body:
                placeholder_hits.append("usage example")

        if placeholder_hits:
            emit("")
            emit("[!] README.md still contains placeholder text for: " + ", ".join(placeholder_hits) + ".")
            emit("    Visitors will see literal `<…>` strings. Fix one of these ways:")
            emit("      1. Edit README.md by hand, then `git commit -am 'fill in README' && git push`.")
            emit("      2. Re-run with the real values:")
            emit(f"         python3 scripts/publish.py {args.path} \\")
            emit("           --install-cmd \"…\" --usage-example \"…\" --regenerate-docs")
            emit(f"         then `git -C {project_path} commit -am 'update README' && git push`.")

        emit("")
        emit("Next steps (this tool stops here — these are all manual / your call):")
        emit(f"  Open the repo:        {repo_url}")
        emit("  Add description + topics (5 short keywords): repo page -> ⚙ About -> Edit")
        emit("  Want a release tag?   git tag v0.1.0 && git push origin v0.1.0")
        emit("  Want README badges?   https://shields.io picks the badge; paste at top of README")
        emit("  Want Discussions?     Settings -> Features -> tick Discussions")
        emit("  Want a launch tweet?  Use a separate writing tool (out of scope)")
        emit("  Want CI?              Write your own .github/workflows/*.yml (out of scope)")
        return _final(args.format, output_lines, state, 0)
    emit("")
    emit("Push reported success but remote verify failed. Check the URL above manually.")
    return _final(args.format, output_lines, state, 1)


def _final(fmt: str, lines: list[str], state: dict[str, Any], exit_code: int) -> int:
    if fmt == "json":
        print(json.dumps({"exit_code": exit_code, "log": lines, "state": state},
                         ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
