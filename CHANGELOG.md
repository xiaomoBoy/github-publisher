# Changelog

All notable changes to this project will be documented in this file. Format loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- Bilingual documentation suite (EN + 中文): README, INSTALL, USAGE, TROUBLESHOOTING, SECURITY, FAQ
- CONTRIBUTING.md with project scope, dev setup, and template-addition guides
- This CHANGELOG.md
- `examples/` directory with three try-it-without-risk sample projects:
  - `minimal-python/` — a 5-line script with no scaffolding
  - `minimal-claude-skill/` — a skeleton Claude skill
  - `with-secrets-fail-demo/` — intentionally leaks a fake OpenAI key so users can see the scanner refuse to publish
- `publish.py --dry-run` — zero-side-effect preview: runs preflight + detect + scan + prints the plan; does **not** write files, `git init`, or commit. Safe for first-time exploration
- Post-publish "next steps" output: after Phase 7 success, prints suggestions for description / topics / tags / badges / Discussions, with explicit anti-scope-creep callouts for tweets / CI
- Post-publish placeholder warning: if `README.md` still contains the literal `<install instructions go here>` or `<usage example goes here>` strings after push, prints a loud warning with two fix paths
- `preflight.py` soft warning for personal email domains (gmail / outlook / qq / etc.) — status stays `[OK]` but the details line tells the user the email will be public, with a pointer to the noreply alias setup

### Changed
- README rewritten as a proper landing page with documentation index, AI assistant matrix, and explicit non-goals

## [0.1.1] — 2026-05-25

### Added
- `publish.py`: `--type`, `--install-cmd`, `--usage-example`, `--regenerate-docs` flags
- `generate_files.py`: `claude-skill` project type maps to `python.gitignore` (most Claude skills are Python + Markdown)
- `scan_project.py`: `scan-ignore-file` marker for documentation files that legitimately contain example secret/path patterns
- `scan_project.py`: attribution scan limited to code-file extensions (`.py`, `.js`, `.rs`, etc.) — eliminates false positives in README templates and license text

### Changed
- `publish.py`: phase numbering renumbered to 1-2-3-4-5-6-7 with no gap. Pre-push review is now a labeled block, not a numbered phase
- `publish.py`: scan-result intermediate JSON moved to `tempfile` (was polluting the project root and being re-scanned on subsequent runs)
- `preflight.py`: each check carries a `required` field; `format_human` uses `[~]  (optional)` for non-required `needs_setup` instead of the loud `[!!]` (so "not logged into `gh`" no longer looks like a blocker)
- `scan_project.py`: ancestor-relationship dedup for third-party directories now uses `Path.parts` instead of string `startswith`, fixing Windows path-separator inconsistency
- `create_repo_safe.py`: safety check refuses to overwrite an existing `origin` remote without `--force-overwrite-origin` (exit code 4)
- `LICENSE` templates for Apache-2.0 and GPL-3.0 are now the canonical full text (was 25-line short attributions previously)
- `scan_project.py`, `generate_files.py`, three reference documents: opted into `scan-ignore-file` because they self-match their own patterns
- `SKILL.md`: reworded one pattern example that was self-matching the scanner

### Fixed
- All four issues surfaced by the recursive dogfood: claude-skill default gitignore, phase number gap, idempotent regeneration of generated files, preflight icon scaring users about non-required items

## [0.1.0] — 2026-05-25

Initial public release. <https://github.com/xiaomoBoy/github-publisher>

### Features
- 7-phase publish pipeline: preflight → detect → scan → generate → git → create+push → verify
- Three-layer scan: private data (secrets / hardcoded paths / sensitive filenames), attribution (forks / third-party code / attribution comments), large files
- Three-path GitHub auth fallback: `gh` CLI → API + keychain PAT → manual web walkthrough
- Newbie-friendly defaults: Public + MIT + auto-detected project type
- Cross-platform: macOS and Windows (Linux likely works, unverified)
- Stdlib only: no `pip install` needed
- AI assistant integration via `SKILL.md` (Claude Code, Copilot CLI, Gemini CLI, etc.)
- Hard constraints: refuses on RED scan; push requires explicit `--yes`; tokens never enter conversation context; never rewrites history; never modifies user code; never changes GitHub settings on the user's behalf
- License chooser docs and three license templates (MIT, Apache-2.0, GPL-3.0) shipped
- gitignore templates: python, node, shell, docs, general
- README templates: basic, with-fork-attribution, with-acknowledgements
