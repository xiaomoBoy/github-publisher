#!/usr/bin/env python3
# scan-ignore-file: docstring naturally describes behavior using phrases like
# "based on scan_project.py findings" — these are not third-party attribution.
"""
Generate the three essentials for a GitHub project: README, LICENSE, .gitignore.
Optionally augments README with fork attribution / acknowledgements / platform compatibility
based on scan_project.py findings.

Works on macOS and Windows. Standard library only.

Usage:
  python3 generate_files.py <project-path> \\
      --license MIT \\
      --type python \\
      --name my-project \\
      --description "One-line description" \\
      --author "your-name" \\
      --tested-on macOS \\
      [--scan-result <path-to-scan-json>] \\
      [--force]

If --scan-result is provided, README gets augmented based on attribution findings.
If --force is not set, will not overwrite existing files.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

SKILL_DIR = Path(__file__).resolve().parent.parent
REFS = SKILL_DIR / "references"


def load_template(rel_path: str) -> str:
    p = REFS / rel_path
    if not p.exists():
        raise FileNotFoundError(f"Template not found: {p}")
    return p.read_text(encoding="utf-8")


def render(template: str, **values: str) -> str:
    out = template
    for key, val in values.items():
        out = out.replace("{" + key + "}", val)
    return out


def write_file(path: Path, content: str, force: bool, label: str) -> tuple[bool, str]:
    if path.exists() and not force:
        return False, f"{label} already exists, skipped (use --force to overwrite)"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True, f"{label} written: {path}"


def generate_license(
    license_name: str,
    year: int,
    holder: str,
    dest: Path,
    force: bool,
) -> tuple[bool, str]:
    tmpl_map = {
        "MIT": "license-templates/MIT.txt",
        "Apache-2.0": "license-templates/Apache-2.0.txt",
        "GPL-3.0": "license-templates/GPL-3.0.txt",
    }
    if license_name not in tmpl_map:
        return False, f"unknown license: {license_name} (use MIT / Apache-2.0 / GPL-3.0)"
    tmpl = load_template(tmpl_map[license_name])
    body = tmpl.replace("{YEAR}", str(year)).replace("{COPYRIGHT_HOLDER}", holder)
    return write_file(dest / "LICENSE", body, force, "LICENSE")


def generate_gitignore(
    project_type: str,
    dest: Path,
    force: bool,
) -> tuple[bool, str]:
    # Map project_type to template; fall back to general.
    # claude-skill maps to python because ~all Claude skills are Python scripts
    # + Markdown docs. Authors writing a Node skill can override with --type node.
    type_map = {
        "python": "python.gitignore",
        "node": "node.gitignore",
        "shell": "shell.gitignore",
        "docs": "docs.gitignore",
        "claude-skill": "python.gitignore",
    }
    tmpl_file = type_map.get(project_type, "general.gitignore")
    body = load_template(f"gitignore-templates/{tmpl_file}")
    return write_file(dest / ".gitignore", body, force, ".gitignore")


def build_acknowledgements_list(scan_result: dict[str, Any]) -> str:
    """Build the markdown bullet list for ## Acknowledgements section."""
    lines = []
    attr = scan_result.get("attribution", {})

    for d in attr.get("third_party_dirs", []):
        dir_path = d.get("dir", "?")
        license_files = d.get("license_files", [])
        if license_files:
            lines.append(f"- `{dir_path}/` — [Original project name from {license_files[0]}] [需要你补全]")
        else:
            lines.append(f"- `{dir_path}/` — [Original project name and source URL] [需要你补全]")

    for c in attr.get("attribution_comments", [])[:10]:
        f = c.get("file", "?")
        ln = c.get("line", "?")
        match = c.get("match", "")[:100]
        lines.append(f"- `{f}:{ln}` — {match} [需要你补全 source URL/作者]")

    more = len(attr.get("attribution_comments", [])) - 10
    if more > 0:
        lines.append(f"- ... and {more} more attribution comments — see scan report for full list")

    if not lines:
        return "- [No third-party code detected — remove this section if it's truly all your own work]"

    return "\n".join(lines)


def pick_readme_template(scan_result: dict[str, Any]) -> str:
    """Choose which README template based on scan findings."""
    attr = scan_result.get("attribution", {}) if scan_result else {}
    if attr.get("is_fork"):
        return "readme-templates/with-fork-attribution.md"
    if attr.get("third_party_dirs") or attr.get("attribution_comments"):
        return "readme-templates/with-acknowledgements.md"
    return "readme-templates/basic.md"


def generate_readme(
    *,
    dest: Path,
    project_name: str,
    description: str,
    author: str,
    author_url: str,
    license_name: str,
    license_file: str,
    repo_url: str,
    tested_on: str,
    install_cmd: str,
    usage_example: str,
    scan_result: dict[str, Any] | None,
    force: bool,
) -> tuple[bool, str]:
    tmpl_path = pick_readme_template(scan_result or {})
    tmpl = load_template(tmpl_path)

    values = {
        "PROJECT_NAME": project_name,
        "ONE_LINE_DESCRIPTION": description,
        "AUTHOR": author,
        "AUTHOR_URL": author_url,
        "LICENSE": license_name,
        "LICENSE_FILE": license_file,
        "REPO_URL": repo_url,
        "TESTED_PLATFORMS": tested_on,
        "INSTALL_COMMAND": install_cmd,
        "USAGE_EXAMPLE": usage_example,
    }

    # If fork template, fill upstream placeholders with TODO markers if not provided
    if "with-fork-attribution" in tmpl_path:
        attr = (scan_result or {}).get("attribution", {})
        upstream_url = ""
        for sig in attr.get("fork_signals", []):
            if sig.get("type") == "git_remote_upstream":
                upstream_url = sig.get("url", "")
                break
        values.update({
            "UPSTREAM_NAME": "[需要你补全 upstream 名称]",
            "UPSTREAM_URL": upstream_url or "[需要你补全 upstream URL]",
            "UPSTREAM_AUTHOR": "[需要你补全 原作者]",
            "UPSTREAM_LICENSE": "[需要你补全 upstream license]",
            "WHY_FORK_OR_SHORT_DESCRIPTION": description or "[一句话说明你为什么 fork / 你的版本做了什么]",
            "CHANGE_1": "[改动 1]",
            "CHANGE_2": "[改动 2]",
        })

    # If acknowledgements template, fill the list from scan
    if "with-acknowledgements" in tmpl_path:
        values["ACKNOWLEDGEMENTS_LIST"] = build_acknowledgements_list(scan_result or {})

    body = render(tmpl, **values)
    return write_file(dest / "README.md", body, force, "README.md")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate README + LICENSE + .gitignore.")
    parser.add_argument("path", help="Project root path")
    parser.add_argument("--license", default="MIT", help="License identifier (MIT / Apache-2.0 / GPL-3.0)")
    parser.add_argument("--type", default="general", help="Project type (python / node / shell / docs / general)")
    parser.add_argument("--name", required=True, help="Project name")
    parser.add_argument("--description", default="", help="One-line description")
    parser.add_argument("--author", required=True, help="Author / GitHub username")
    parser.add_argument("--author-url", default="", help="Author URL (defaults to https://github.com/<author>)")
    parser.add_argument("--repo-url", default="", help="Repo URL (defaults to https://github.com/<author>/<name>)")
    parser.add_argument("--year", type=int, default=datetime.now().year)
    parser.add_argument("--tested-on", default="macOS", help="Platforms tested on (e.g. 'macOS' or 'macOS and Windows')")
    parser.add_argument("--install-cmd", default="<install instructions go here>")
    parser.add_argument("--usage-example", default="<usage example goes here>")
    parser.add_argument("--scan-result", help="Path to scan_project.py JSON output (for attribution augmentation)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    args = parser.parse_args()

    root = Path(args.path).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 1

    author_url = args.author_url or f"https://github.com/{args.author}"
    repo_url = args.repo_url or f"https://github.com/{args.author}/{args.name}"

    scan_result = None
    if args.scan_result:
        scan_path = Path(args.scan_result).expanduser().resolve()
        if scan_path.exists():
            try:
                scan_result = json.loads(scan_path.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"warning: could not load scan result: {e}", file=sys.stderr)

    results = []

    ok, msg = generate_license(args.license, args.year, args.author, root, args.force)
    results.append({"file": "LICENSE", "ok": ok, "message": msg})

    ok, msg = generate_gitignore(args.type, root, args.force)
    results.append({"file": ".gitignore", "ok": ok, "message": msg})

    ok, msg = generate_readme(
        dest=root,
        project_name=args.name,
        description=args.description or f"{args.name} — a project",
        author=args.author,
        author_url=author_url,
        license_name=args.license,
        license_file="LICENSE",
        repo_url=repo_url,
        tested_on=args.tested_on,
        install_cmd=args.install_cmd,
        usage_example=args.usage_example,
        scan_result=scan_result,
        force=args.force,
    )
    results.append({"file": "README.md", "ok": ok, "message": msg})

    print(json.dumps({"results": results}, ensure_ascii=False, indent=2))
    return 0 if all(r["ok"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
