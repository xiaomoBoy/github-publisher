# github-publisher

> Publish any local project to GitHub with one sentence — `"open source /path/to/my-project"`.
> Built for first-timers and non-coders. Security-aware. Stdlib only. macOS + Windows.

中文文档 → [README.zh.md](README.zh.md)

---

## What this is

A reusable AI skill (and standalone Python tool) that takes a local folder and turns it into a published GitHub repository, safely. It is meant for people who:

- have never open-sourced anything before and don't want to learn 12 commands
- already know git but don't want to manually write `README` / `LICENSE` / `.gitignore` every time
- want a second pair of eyes that **refuses to push if a secret leaked into the code**

You can drive it through an AI assistant ("open source this folder") or run the Python scripts directly. Either way, the same scripts do the work — no magic in the AI layer.

## Quick start

```bash
# 1. Install
git clone https://github.com/xiaomoBoy/github-publisher.git ~/.claude/skills/github-publisher

# 2. Check your environment
python3 ~/.claude/skills/github-publisher/scripts/preflight.py

# 3. Publish
#    With an AI assistant (Claude Code, etc.):
#      "open source /path/to/my-project"
#    Standalone:
python3 ~/.claude/skills/github-publisher/scripts/publish.py /path/to/my-project
# Review the printed plan, then re-run with --yes to confirm push:
python3 ~/.claude/skills/github-publisher/scripts/publish.py /path/to/my-project --yes
```

Full instructions: [INSTALL.md](INSTALL.md) · [USAGE.md](USAGE.md) · [TROUBLESHOOTING.md](TROUBLESHOOTING.md) · [SECURITY.md](SECURITY.md)

## What it does (7 phases)

| # | Phase | What runs | What it produces |
|---|---|---|---|
| 1 | Preflight | `preflight.py` | Reports what's missing (git? gh? PAT?) with per-OS install commands |
| 2 | Detect | `detect_project_type.py` | Guesses project type (Python / Node / Claude skill / etc.) |
| 3 | Scan | `scan_project.py` | Three-layer scan: secrets, attribution, large files. RED ⇒ refuses to continue |
| 4 | Generate | `generate_files.py` | Writes `README.md`, `LICENSE`, `.gitignore` from templates |
| 5 | Local git | `publish.py` | `git init` + `git add -A` + initial `commit` (skipped if already done) |
| — | Pre-push review | `publish.py` | Prints the plan and stops, waiting for explicit `--yes` |
| 6 | Create + push | `create_repo_safe.py` | Three fallback paths: `gh CLI` → API + keychain PAT → manual web walkthrough |
| 7 | Verify | `verify_remote.py` | Confirms HEAD matches and key files are on the remote |

## Hard constraints (the tool will refuse to violate these)

1. **Refuses to push if any RED scan finding** (secret / private path / sensitive filename / oversized file)
2. **Push requires explicit `--yes`** — never silent, never implied
3. **Tokens never enter the conversation context** — pulled from OS keychain via `git credential fill`, written to a 0600 tempfile, shredded after use
4. **Never deletes any local file or modifies code** — only writes new files (`README.md`, `LICENSE`, `.gitignore`)
5. **Never changes GitHub settings** for you (visibility, branch protection, Discussions, secrets — your job)
6. **Never rewrites git history** (`filter-branch`, `rebase -i`, `git rm` from history are all off-limits)
7. **Never decides whether your project *should* be open-sourced** — it lists evidence; the call is yours

## Decision defaults (you don't have to think about these)

| Decision | Default | Why |
|---|---|---|
| Visibility | **Public** | This is an "open source" tool. Want private first? Override with `--private`, or flip in GitHub Settings afterwards |
| License | **MIT** | Most permissive, most common, lowest blast radius for first-timers |
| Project type | Auto-detected | Determines which `.gitignore` template you get |
| Add-ons (CONTRIBUTING / CHANGELOG / templates / badges) | **Off** | Generate them later when you actually need them |

Override any of these with command-line flags — see [USAGE.md](USAGE.md).

## AI assistant support

The skill ships as a single directory and works with anything that loads Claude-style skills:

| Assistant | Install path | How it triggers |
|---|---|---|
| Claude Code (CLI / web / IDE) | `~/.claude/skills/github-publisher/` | `SKILL.md` description matches phrases like "open source XX" |
| Cursor / Copilot CLI (with skill loader) | Equivalent skill directory | Same `SKILL.md` |
| Any other AI tool that reads `SKILL.md` | Anywhere | Point it at the directory |
| **No AI at all** | Anywhere | Run the Python scripts directly. See [USAGE.md](USAGE.md) |

The AI layer is just an orchestrator. The actual logic lives in `scripts/*.py` — no AI is required to publish.

## What this tool will NOT do (use other tools)

| You want | Use |
|---|---|
| Publish to npm / pip / cargo | The respective package registry's release flow |
| Configure CI / GitHub Actions | Hand-write your `.github/workflows/*.yml` |
| Write a launch tweet / blog post | A separate writing tool |
| Change visibility, add Discussions, add branch protection | Do it manually in GitHub Settings (you must own that risk) |
| Rewrite git history to scrub leaked secrets | [`git-filter-repo`](https://github.com/newren/git-filter-repo) or [BFG](https://rtyley.github.io/bfg-repo-cleaner/) |
| Translate your README to another language | Manually, or a translation tool |
| Test on Linux | Not validated; PRs welcome |

## Platform support

Tested on **macOS** and **Windows**. Linux likely works (everything is stdlib Python and standard git/gh commands) but is unverified.

All scripts use Python `pathlib` / `subprocess` / `urllib` / `tempfile` / `shutil` — no `bash` features, no third-party packages.

## Documentation

| Document | What's in it |
|---|---|
| [README.md](README.md) | This page |
| [README.zh.md](README.zh.md) | Chinese version |
| [INSTALL.md](INSTALL.md) · [INSTALL.zh.md](INSTALL.zh.md) | Install per OS, per AI client, plus auth setup |
| [USAGE.md](USAGE.md) · [USAGE.zh.md](USAGE.zh.md) | Every flag, every exit code, every phase explained |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) · [TROUBLESHOOTING.zh.md](TROUBLESHOOTING.zh.md) | Common errors and fixes |
| [SECURITY.md](SECURITY.md) · [SECURITY.zh.md](SECURITY.zh.md) | Security model, what's protected, what's not |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Dev setup, code style, how to add templates |
| [CHANGELOG.md](CHANGELOG.md) | Version history |
| `SKILL.md` | The skill manifest — describes the workflow to AI assistants |
| `references/` | Pattern docs, license/gitignore/README templates, fix recipes |

## License

MIT — see [LICENSE](LICENSE).

Built by [@xiaomoBoy](https://github.com/xiaomoBoy).
