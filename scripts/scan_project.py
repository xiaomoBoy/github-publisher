#!/usr/bin/env python3
# scan-ignore-file: this file contains the pattern source itself; it will
# always self-match. Real secrets in this file would be caught by code review.
"""
Three-layer pre-publication scanner for github-publisher skill.

Scans:
  1. Private data: hardcoded user paths, secret patterns, sensitive filenames
  2. Attribution: fork signals, third-party code, attribution comments
  3. Large files (>50 MB)

Outputs JSON to stdout. status field: red (any private-data finding) /
yellow (only weak findings) / green (clean).

Works on macOS and Windows. Standard library only.

Usage:
  python3 scan_project.py <project-path>
  python3 scan_project.py <project-path> --format human
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

PRIVATE_PATH_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("user_path_macos", re.compile(r"/Users/[^/\s'\"<>]+")),
    ("user_path_linux", re.compile(r"/home/[^/\s'\"<>]+")),
    ("user_path_windows_backslash", re.compile(r"[Cc]:\\\\Users\\\\[^\\\\\s'\"<>]+")),
    ("user_path_windows_forward", re.compile(r"[Cc]:/Users/[^/\s'\"<>]+")),
]

STRONG_SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("openai", re.compile(r"sk-(?:proj-)?[A-Za-z0-9]{20,}")),
    ("anthropic", re.compile(r"sk-ant-[A-Za-z0-9\-_]{20,}")),
    ("github_pat_classic", re.compile(r"ghp_[A-Za-z0-9]{36}")),
    ("github_pat_fine", re.compile(r"github_pat_[A-Za-z0-9_]{82}")),
    ("github_oauth", re.compile(r"gho_[A-Za-z0-9]{36}")),
    ("aws_access_key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("slack_bot", re.compile(r"xoxb-[0-9]+-[0-9]+-[A-Za-z0-9]+")),
    ("slack_user", re.compile(r"xoxp-[0-9]+-[0-9]+-[0-9]+-[a-z0-9]+")),
    ("google_api", re.compile(r"AIza[0-9A-Za-z\-_]{35}")),
    ("stripe_live", re.compile(r"sk_live_[A-Za-z0-9]{24,}")),
    ("stripe_test", re.compile(r"sk_test_[A-Za-z0-9]{24,}")),
    ("private_key_header", re.compile(r"-----BEGIN (?:RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("pgp_private", re.compile(r"-----BEGIN PGP PRIVATE KEY BLOCK-----")),
]

WEAK_SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("password_assign", re.compile(
        r"""(?ix) (?:^|\W) password \s* [=:] \s* ['"]([^'"\s]{6,})['"] """
    )),
    ("token_assign", re.compile(
        r"""(?ix) (?:^|\W) (?:api[_-]?)? token \s* [=:] \s* ['"]([^'"\s]{16,})['"] """
    )),
    ("api_key_assign", re.compile(
        r"""(?ix) (?:^|\W) api[_-]?key \s* [=:] \s* ['"]([^'"\s]{16,})['"] """
    )),
]

SENSITIVE_FILENAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    "credentials.json",
    "credentials.yaml",
    "credentials.yml",
    "secrets.json",
    "secrets.yaml",
    "secrets.yml",
    ".npmrc",
    ".pypirc",
    ".netrc",
    "id_rsa",
    "id_rsa.pub",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "id_ed25519.pub",
}

SENSITIVE_FILENAME_SUFFIXES = {".key", ".pem", ".pfx", ".p12", ".tfstate", ".tfvars"}

SENSITIVE_FILENAME_EXCEPTIONS = {
    ".env.example",
    ".env.template",
    ".env.sample",
    "id_rsa.example",
}

# Attribution-comment scanning only runs on real code files. Markdown / text /
# template files routinely contain phrases like "based on" or "Original by" in
# prose, README templates, or legal text — those are not attribution markers.
ATTRIBUTION_CODE_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".mjs",
    ".rs", ".go", ".java", ".kt", ".scala",
    ".c", ".cc", ".cpp", ".h", ".hpp",
    ".rb", ".php", ".cs", ".swift",
    ".sh", ".bash", ".zsh", ".fish",
    ".ex", ".exs", ".erl",
    ".lua", ".pl", ".pm",
}

ATTRIBUTION_COMMENT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("adapted_from", re.compile(r"(?i)adapted\s+from")),
    ("based_on", re.compile(r"(?i)based\s+on")),
    ("derived_from", re.compile(r"(?i)derived\s+from")),
    ("original_by", re.compile(r"(?i)original(?:ly)?\s+(?:written\s+)?by")),
    ("jsdoc_author", re.compile(r"@author\s+\S")),
    ("credits", re.compile(r"(?i)credits?\s*:")),
    ("copyright", re.compile(r"(?i)copyright\s*(?:\(c\)|©)?\s*\d{4}")),
    ("modified_from", re.compile(r"(?i)modified\s+from")),
    ("fork_of", re.compile(r"(?i)fork\s+of")),
    ("borrowed_from", re.compile(r"(?i)borrowed\s+from")),
]

THIRD_PARTY_DIRS = {
    "vendor",
    "third_party",
    "3rdparty",
    "external",
    "deps",
    "external-libs",
}

SKIP_DIRS = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    ".next",
    ".nuxt",
    ".cache",
    "target",
    ".idea",
    ".vscode",
}

BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ico", ".svg",
    ".mp3", ".mp4", ".avi", ".mov", ".webm", ".wav", ".flac",
    ".zip", ".tar", ".gz", ".bz2", ".7z", ".rar",
    ".exe", ".dll", ".dylib", ".so", ".bin",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".pyc", ".pyo",
    ".class", ".jar",
    ".whl",
}

LARGE_FILE_THRESHOLD_MB = 50

MAX_LINE_LENGTH_SCAN = 5000  # don't try to scan single huge lines (minified JS etc)

# Files whose first 2 KB contain this marker are treated as documentation-only
# (e.g. pattern reference docs, fix-recipe tutorials) and skipped for secret /
# private-data scanning. Attribution scanning still applies.
SCAN_IGNORE_MARKER = "scan-ignore-file"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def iter_files(root: Path) -> list[Path]:
    """Yield all files under root, skipping SKIP_DIRS."""
    out: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        out.append(path)
    return out


def is_text_file(path: Path) -> bool:
    if path.suffix.lower() in BINARY_EXTENSIONS:
        return False
    try:
        with path.open("rb") as f:
            chunk = f.read(8192)
        if b"\x00" in chunk:
            return False
        return True
    except OSError:
        return False


def read_text_safe(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def has_scan_ignore_marker(path: Path) -> bool:
    """True if the file's first 2 KB contains SCAN_IGNORE_MARKER."""
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            head = f.read(2048)
        return SCAN_IGNORE_MARKER in head
    except OSError:
        return False


def is_sensitive_filename(path: Path) -> bool:
    name = path.name
    if name in SENSITIVE_FILENAME_EXCEPTIONS:
        return False
    if name in SENSITIVE_FILENAMES:
        return True
    suffix = path.suffix.lower()
    if suffix in SENSITIVE_FILENAME_SUFFIXES:
        return True
    return False


def run_git(args: list[str], cwd: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return None
        return result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


# ---------------------------------------------------------------------------
# Layer 1: Private data
# ---------------------------------------------------------------------------

def scan_private_data(files: list[Path], root: Path) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    for path in files:
        rel = path.relative_to(root)

        # Sensitive filename — flag regardless of content
        if is_sensitive_filename(path):
            findings.append({
                "category": "sensitive_file",
                "type": "filename_match",
                "file": str(rel),
                "line": None,
                "match_preview": path.name,
                "severity": "red",
                "fix_hint": "Add this filename to .gitignore and remove from tracking. See references/secret-fix-recipes.md §6.",
            })
            # still scan its content below if text

        if not is_text_file(path):
            continue

        # Documentation-only files (pattern refs, fix recipes) opt out via marker
        if has_scan_ignore_marker(path):
            continue

        text = read_text_safe(path)
        if text is None:
            continue

        for lineno, line in enumerate(text.splitlines(), 1):
            if len(line) > MAX_LINE_LENGTH_SCAN:
                continue

            # Private paths
            for name, pat in PRIVATE_PATH_PATTERNS:
                for m in pat.finditer(line):
                    findings.append({
                        "category": "private_path",
                        "type": name,
                        "file": str(rel),
                        "line": lineno,
                        "match_preview": m.group()[:80],
                        "severity": "red",
                        "fix_hint": "See references/secret-fix-recipes.md §7.",
                    })

            # Strong secrets
            for name, pat in STRONG_SECRET_PATTERNS:
                for m in pat.finditer(line):
                    findings.append({
                        "category": "strong_secret",
                        "type": name,
                        "file": str(rel),
                        "line": lineno,
                        "match_preview": redact(m.group()),
                        "severity": "red",
                        "fix_hint": f"See references/secret-fix-recipes.md (search '{name}').",
                    })

            # Weak secrets
            for name, pat in WEAK_SECRET_PATTERNS:
                for m in pat.finditer(line):
                    findings.append({
                        "category": "weak_secret",
                        "type": name,
                        "file": str(rel),
                        "line": lineno,
                        "match_preview": redact(m.group()[:80]),
                        "severity": "yellow",
                        "fix_hint": "Confirm with user whether this is a real secret; if yes, see references/secret-fix-recipes.md.",
                    })

    return findings


def redact(s: str) -> str:
    """Mask middle of a string so it doesn't get logged."""
    if len(s) <= 12:
        return s[:3] + "***"
    return s[:6] + "...REDACTED..." + s[-4:]


# ---------------------------------------------------------------------------
# Layer 2: Attribution
# ---------------------------------------------------------------------------

def scan_attribution(files: list[Path], root: Path) -> dict[str, Any]:
    out: dict[str, Any] = {
        "is_fork": False,
        "fork_signals": [],
        "third_party_dirs": [],
        "attribution_comments": [],
    }

    # Fork signal A: git remote
    remotes = run_git(["remote", "-v"], root)
    if remotes:
        for line in remotes.splitlines():
            if "upstream" in line.lower() and ("(fetch)" in line or "(push)" in line):
                parts = line.split()
                if len(parts) >= 2:
                    out["is_fork"] = True
                    out["fork_signals"].append({
                        "type": "git_remote_upstream",
                        "url": parts[1],
                    })
                    break

    # Fork signal B: manifest files
    for manifest_name in ("package.json", "pyproject.toml", "Cargo.toml"):
        manifest = root / manifest_name
        if not manifest.exists():
            continue
        text = read_text_safe(manifest) or ""
        # very loose detection
        if re.search(r"(?i)(forkedFrom|forked_from|fork_of)", text):
            out["is_fork"] = True
            out["fork_signals"].append({
                "type": "manifest_fork_field",
                "file": manifest_name,
            })

    # Third-party dirs: dedupe by dir path. A parent already listed swallows children.
    # Use Path-based ancestor check so Windows backslash separators work.
    seen_dirs: dict[str, dict[str, Any]] = {}

    def _is_ancestor(ancestor: str, descendant: str) -> bool:
        """True if `ancestor` is a (proper or equal) ancestor of `descendant`,
        independent of path separator (works on both Windows and POSIX)."""
        a_parts = Path(ancestor).parts
        d_parts = Path(descendant).parts
        return len(a_parts) <= len(d_parts) and d_parts[: len(a_parts)] == a_parts

    def add_third_party(dir_rel: str, license_files: list[str]) -> None:
        # If this dir or any ancestor is already recorded, merge into the existing entry
        for existing in list(seen_dirs.keys()):
            if _is_ancestor(existing, dir_rel):
                for lf in license_files:
                    if lf not in seen_dirs[existing]["license_files"]:
                        seen_dirs[existing]["license_files"].append(lf)
                if license_files:
                    seen_dirs[existing]["has_license_file"] = True
                return
            # If this new dir is an ancestor of an existing entry, swallow the existing one
            if _is_ancestor(dir_rel, existing) and dir_rel != existing:
                old = seen_dirs.pop(existing)
                license_files = list({*license_files, *old["license_files"]})
        seen_dirs[dir_rel] = {
            "dir": dir_rel,
            "has_license_file": bool(license_files),
            "license_files": license_files[:5],
        }

    for path in root.iterdir():
        if not path.is_dir():
            continue
        if path.name in THIRD_PARTY_DIRS:
            license_files = list(path.rglob("LICENSE*")) + list(path.rglob("COPYING*"))
            add_third_party(
                str(path.relative_to(root)),
                [str(p.relative_to(root)) for p in license_files[:5]],
            )

    # Sub-directories with LICENSE (anywhere, not just THIRD_PARTY_DIRS)
    for license_path in root.rglob("LICENSE*"):
        if any(part in SKIP_DIRS for part in license_path.parts):
            continue
        # skip the root LICENSE (that's ours)
        if license_path.parent == root:
            continue
        add_third_party(
            str(license_path.parent.relative_to(root)),
            [str(license_path.relative_to(root))],
        )

    out["third_party_dirs"] = list(seen_dirs.values())

    # Attribution comments — only in real code files. Prose / templates /
    # license text routinely contain these phrases benignly.
    for path in files:
        if path.suffix.lower() not in ATTRIBUTION_CODE_EXTENSIONS:
            continue
        if not is_text_file(path):
            continue
        if path.name.upper().startswith(("LICENSE", "NOTICE", "COPYING")):
            continue
        if has_scan_ignore_marker(path):
            continue
        text = read_text_safe(path)
        if text is None:
            continue
        rel = path.relative_to(root)
        for lineno, line in enumerate(text.splitlines(), 1):
            if len(line) > MAX_LINE_LENGTH_SCAN:
                continue
            for name, pat in ATTRIBUTION_COMMENT_PATTERNS:
                if pat.search(line):
                    out["attribution_comments"].append({
                        "type": name,
                        "file": str(rel),
                        "line": lineno,
                        "match": line.strip()[:120],
                    })
                    break  # one finding per line

    return out


# ---------------------------------------------------------------------------
# Layer 3: Large files
# ---------------------------------------------------------------------------

def scan_large_files(files: list[Path], root: Path) -> list[dict[str, Any]]:
    threshold = LARGE_FILE_THRESHOLD_MB * 1024 * 1024
    out: list[dict[str, Any]] = []
    for path in files:
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size >= threshold:
            out.append({
                "file": str(path.relative_to(root)),
                "size_mb": round(size / 1024 / 1024, 2),
                "severity": "yellow" if size < 100 * 1024 * 1024 else "red",
            })
    return out


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def scan(root: Path) -> dict[str, Any]:
    files = iter_files(root)

    private_findings = scan_private_data(files, root)
    attribution = scan_attribution(files, root)
    large_files = scan_large_files(files, root)

    summary = {
        "files_scanned": len(files),
        "private_paths": sum(1 for f in private_findings if f["category"] == "private_path"),
        "strong_secrets": sum(1 for f in private_findings if f["category"] == "strong_secret"),
        "weak_secrets": sum(1 for f in private_findings if f["category"] == "weak_secret"),
        "sensitive_files": sum(1 for f in private_findings if f["category"] == "sensitive_file"),
        "is_fork": attribution["is_fork"],
        "third_party_dirs": len(attribution["third_party_dirs"]),
        "attribution_comments": len(attribution["attribution_comments"]),
        "large_files": len(large_files),
    }

    # Status: red if any red-severity finding; yellow if only weak/yellow; green otherwise.
    has_red = any(f.get("severity") == "red" for f in private_findings) \
        or any(lf.get("severity") == "red" for lf in large_files)
    has_yellow = any(f.get("severity") == "yellow" for f in private_findings) \
        or any(lf.get("severity") == "yellow" for lf in large_files)

    if has_red:
        status = "red"
    elif has_yellow:
        status = "yellow"
    else:
        status = "green"

    return {
        "status": status,
        "summary": summary,
        "private_findings": private_findings,
        "attribution": attribution,
        "large_files": large_files,
        "notes": [
            "git history is NOT scanned. If you previously committed secrets, see references/secret-fix-recipes.md.",
        ],
    }


def format_human(result: dict[str, Any]) -> str:
    lines = []
    status = result["status"]
    s = result["summary"]
    lines.append(f"=== Scan result: {status.upper()} ===")
    lines.append(f"Files scanned: {s['files_scanned']}")
    lines.append(f"Private paths: {s['private_paths']}  Strong secrets: {s['strong_secrets']}  Weak secrets: {s['weak_secrets']}  Sensitive files: {s['sensitive_files']}")
    lines.append(f"Fork: {s['is_fork']}  Third-party dirs: {s['third_party_dirs']}  Attribution comments: {s['attribution_comments']}")
    lines.append(f"Large files (>= {LARGE_FILE_THRESHOLD_MB} MB): {s['large_files']}")
    lines.append("")

    if result["private_findings"]:
        lines.append("--- Private data findings (must fix before publishing) ---")
        for f in result["private_findings"]:
            loc = f"{f['file']}:{f['line']}" if f["line"] else f["file"]
            lines.append(f"  [{f['severity'].upper()}] {f['category']}/{f['type']} @ {loc}")
            lines.append(f"      preview: {f['match_preview']}")
            lines.append(f"      fix: {f['fix_hint']}")
        lines.append("")

    if result["attribution"]["is_fork"] or result["attribution"]["third_party_dirs"] or result["attribution"]["attribution_comments"]:
        lines.append("--- Attribution signals (README will be auto-augmented) ---")
        if result["attribution"]["is_fork"]:
            lines.append("  Detected as fork:")
            for sig in result["attribution"]["fork_signals"]:
                lines.append(f"    - {sig}")
        for d in result["attribution"]["third_party_dirs"]:
            lines.append(f"  Third-party dir: {d['dir']} (has LICENSE: {d['has_license_file']})")
        for c in result["attribution"]["attribution_comments"][:10]:
            lines.append(f"  Comment: {c['file']}:{c['line']}  {c['match']}")
        more = len(result["attribution"]["attribution_comments"]) - 10
        if more > 0:
            lines.append(f"  ... and {more} more attribution comments")
        lines.append("")

    if result["large_files"]:
        lines.append("--- Large files ---")
        for lf in result["large_files"]:
            lines.append(f"  [{lf['severity'].upper()}] {lf['file']}  {lf['size_mb']} MB")
        lines.append("")

    if status == "green":
        lines.append("All clear. Safe to proceed to Phase 3 (file generation).")
    elif status == "yellow":
        lines.append("Yellow warnings. Review weak secrets and large files; if accepted, can proceed.")
    else:
        lines.append("RED warnings. Must resolve before proceeding to Phase 3. See references/secret-fix-recipes.md.")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Three-layer pre-publication scanner (private data + attribution + large files)."
    )
    parser.add_argument("path", help="Project root path")
    parser.add_argument(
        "--format",
        choices=["json", "human"],
        default="human",
        help="Output format (default: human; pass --format json for machine-readable)",
    )
    args = parser.parse_args()

    root = Path(args.path).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 1

    result = scan(root)

    if args.format == "human":
        print(format_human(result))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))

    # Exit code: 0 green, 1 yellow, 2 red — so callers can branch on it
    return {"green": 0, "yellow": 1, "red": 2}[result["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
