# Usage

中文版 → [USAGE.zh.md](USAGE.zh.md)

This document covers:
- [TL;DR](#tldr)
- [Two ways to use it](#two-ways-to-use-it)
- [`publish.py` reference](#publishpy-reference)
- [`preflight.py` reference](#preflightpy-reference)
- [The 7 phases explained](#the-7-phases-explained)
- [Exit codes](#exit-codes)
- [Common scenarios](#common-scenarios)
- [Working with forks and third-party code](#working-with-forks-and-third-party-code)
- [`scan-ignore-file` marker](#scan-ignore-file-marker)
- [Customizing templates](#customizing-templates)
- [Running each script directly](#running-each-script-directly)

---

## TL;DR

```bash
# Through an AI assistant:
# > "open source /path/to/my-project"

# Standalone:
python3 scripts/publish.py /path/to/my-project           # plans, stops, exit 12
python3 scripts/publish.py /path/to/my-project --yes     # actually pushes
```

That's the whole flow. Everything below is detail.

---

## Two ways to use it

### Mode 1 — AI assistant (Quick Mode)

You say: *"open source /path/to/my-project"*.

The AI:
1. Runs `preflight.py`. If anything required is missing, offers to install it (asks you once: `y/n`).
2. Runs `publish.py <path>` with sensible defaults. It stops at "Pre-push review" with exit code 12.
3. Shows you the printed plan and asks: *"push? (y/n)"*.
4. On `y`, re-runs `publish.py <path> --yes` to push and verify.

You interact via exactly two yes/no questions: install missing tools, and confirm push.

### Mode 2 — Standalone (no AI)

You run `publish.py` directly with the flags you want. It still stops before push (exit 12); you re-run with `--yes` to confirm.

Both modes call the same scripts. The AI is convenience, not magic.

---

## `publish.py` reference

```
python3 scripts/publish.py <path> [options]
```

`<path>` is the project root (the folder you want to publish).

### Options

| Flag | Default | What it does |
|---|---|---|
| `--name <name>` | basename of `<path>`, kebab-cased | Repo name on GitHub |
| `--license <id>` | `MIT` | One of `MIT` / `Apache-2.0` / `GPL-3.0` |
| `--public` | (default) | Public repo |
| `--private` | | Private repo |
| `--description "<text>"` | empty | One-line description; appears in the GitHub repo header and README |
| `--author <username>` | auto-detected | GitHub username (used in README + LICENSE). Auto-detected from `gh api user` or git noreply email |
| `--type <type>` | auto-detected | Override project type: `python` / `node` / `shell` / `docs` / `claude-skill` / `general`. Determines which `.gitignore` template you get |
| `--commit-message "<msg>"` | `Initial commit` | The first commit message |
| `--install-cmd "<cmd>"` | placeholder text | Real install instructions for the generated `README.md` |
| `--usage-example "<cmd>"` | placeholder text | Real usage example for the generated `README.md` |
| `--regenerate-docs` | off | Overwrite existing `README.md` / `LICENSE` / `.gitignore`. Default: skip if present (protects manual edits) |
| `--yes` | off | Explicit push confirmation. **Without this, the tool never pushes** |
| `--skip-preflight` | off | Skip Phase 1 |
| `--no-push` | off | Run Phases 1–5 only; skip create + push + verify |
| `--format <fmt>` | `human` | `human` (printed log) or `json` (single JSON blob with full state — for AI consumption) |

### Minimal examples

```bash
# Take all defaults
python3 scripts/publish.py /path/to/my-tool

# Custom name + description
python3 scripts/publish.py /path/to/my-tool \
    --name awesome-tool \
    --description "A nifty CLI for X"

# Private repo
python3 scripts/publish.py /path/to/my-tool --private

# Apache 2.0 license
python3 scripts/publish.py /path/to/my-tool --license Apache-2.0

# Force regenerate README/LICENSE/.gitignore (e.g. after changing --description)
python3 scripts/publish.py /path/to/my-tool --description "New" --regenerate-docs
```

---

## `preflight.py` reference

```
python3 scripts/preflight.py [--format human|json]
```

Reports on:

- `python3` (you're running it, so it's there — but version is printed)
- `git` (installed? version?)
- `git.user.name` / `git.user.email` (configured globally?)
- `gh` CLI (installed?)
- `gh.auth` (logged in?)
- `git.credential` (PAT cached in keychain?)
- `network.github` (can reach `api.github.com`?)

Exit codes:

- `0` — ready (at least one auth path available)
- `1` — required tools missing
- `2` — ready but only manual auth path available

Required items have these names (preflight will tell you the exact install command per OS):

- `python3`
- `git`
- `git.user.name`
- `git.user.email`
- `network.github`

Optional (publish will still work without them, but the flow is smoother with them):

- `gh`
- `gh.auth`
- `git.credential`

---

## The 7 phases explained

### Phase 1 — Preflight

Runs `preflight.py` internally. If any required check fails, `publish.py` aborts with exit 10 — no project changes have been made.

Skipping: `--skip-preflight` skips this phase (useful in CI where you've already verified).

### Phase 2 — Detect project

Runs `detect_project_type.py`. It looks at:

- Manifest files at the root: `package.json` → node, `pyproject.toml` → python, etc.
- The presence of `SKILL.md` → claude-skill
- File extension counts as a fallback
- Whether `.git/` exists and whether there's an `upstream` remote (fork signal)

The detected type feeds Phase 4 (picks the `.gitignore` template). You can override with `--type`.

### Phase 3 — Three-layer scan

Runs `scan_project.py`. Three layers:

| Layer | Looks for | RED finding behavior |
|---|---|---|
| Private data | Hardcoded `/Users/<name>` / `/home/<name>` / `C:\Users\<name>`; strong secret patterns (`sk-…`, `ghp_…`, `AKIA…`, PEM private-key headers, etc.); sensitive filenames (`.env`, `id_rsa`, `*.pem`, etc.) | RED — aborts pipeline with exit 11 |
| Attribution | Fork signals; third-party directories (`vendor/`, `third_party/`, etc.); attribution comments in code files | Informational — README gets augmented |
| Large files | Files > 50 MB | YELLOW; > 100 MB triggers RED (GitHub's hard limit) |

A RED finding **prevents Phase 4 onward**. You must fix the leak (see [`references/secret-fix-recipes.md`](references/secret-fix-recipes.md)) and re-run.

False positives in documentation files? Use the [`scan-ignore-file` marker](#scan-ignore-file-marker).

### Phase 4 — Generate

Runs `generate_files.py`. Writes (unless they already exist):

- `LICENSE` — picked by `--license`, substituted with `{YEAR}` and `{COPYRIGHT_HOLDER}` (= the `--author`)
- `.gitignore` — picked by `--type` (or auto-detected type from Phase 2)
- `README.md` — picked from one of three templates:
  - `basic` — if scan found nothing notable
  - `with-fork-attribution` — if Phase 3 detected a fork signal
  - `with-acknowledgements` — if Phase 3 detected third-party dirs or attribution comments

If any of the three target files already exists, it's **skipped by default**. Use `--regenerate-docs` to overwrite (e.g. after you changed `--description`).

### Phase 5 — Local git

Done by `publish.py` directly (delegates the email/identity checks to `check_git_config.py`):

- `git init -b main` if no `.git/` yet
- Soft-warns if `user.email` looks like a personal email (gmail / outlook / qq / etc.) — never changes anything
- `git add -A`
- `git commit -m "<message>"` — defaults to `Initial commit`; skipped if working tree is clean

### Pre-push review (no number)

Just before push, `publish.py` prints a Plan summary block:

```
=== Pre-push review (re-run with --yes to confirm) ===
  Project path:    /path/to/my-tool
  Repo name:       my-tool
  Visibility:      Public
  License:         MIT
  Description:     ...
  Author:          ...
  Will create:     https://github.com/<author>/my-tool
```

And exits with code 12. **No GitHub-side changes have happened yet.**

To proceed, re-run the exact same command with `--yes`.

### Phase 6 — Create + push

Runs `create_repo_safe.py`. Tries three paths in order:

| Path | Method | When |
|---|---|---|
| A | `gh repo create … --push` | `gh` is installed and logged in |
| B | `urllib` POST to `/user/repos` using PAT from `git credential fill`, then `git push` | `gh` not available but a PAT is cached |
| C | Prints a manual web walkthrough, exits 13 | Neither A nor B works |

Safety check first: if `origin` is already configured to a different URL, refuses with exit 4 and prints three recovery options (just push manually / `--force-overwrite-origin` to replace / `git remote remove origin` and retry). It will not silently overwrite a remote you set yourself.

Token handling (Path B): the PAT is read via `git credential fill` (stays in the OS keychain mechanism), written to a 0600 tempfile, used as a header in the HTTPS API call, then **shredded with random bytes and unlinked**. It never lives in environment variables or stdout.

### Phase 7 — Verify

Runs `verify_remote.py`. Does:

- `git fetch origin --quiet`
- Compares `HEAD` to `origin/main` — must match
- `git ls-tree` of `origin/main` — checks that `README.md`, `LICENSE`, `.gitignore` are all present remotely

If any check fails, exits 1. Otherwise prints the repo URL and a success summary.

---

## Exit codes

| Code | Meaning | What to do |
|---|---|---|
| 0 | Done — repo created and verified | Open the URL printed at the end |
| 1 | Generic error | Read the log to see which phase failed |
| 4 | `origin` already configured to a different URL (Path A/B safety check) | See the printed hint: push manually, or use `--force-overwrite-origin`, or `git remote remove origin` |
| 10 | Preflight: required tools missing | Install per the printed commands and re-run |
| 11 | Scan: RED finding | Fix per `references/secret-fix-recipes.md` and re-run |
| 12 | Pre-push review (no `--yes`) | If the plan looks right, re-run with `--yes` |
| 13 | Auth fell through to Path C (manual) | Follow the printed walkthrough in your browser + terminal |

---

## Common scenarios

### "I just want to publish, take all defaults"

```bash
python3 scripts/publish.py /path/to/folder
# Inspect plan, then:
python3 scripts/publish.py /path/to/folder --yes
```

### "I made a typo in the description and the README already wrote it"

```bash
python3 scripts/publish.py /path/to/folder \
    --description "Corrected description" \
    --regenerate-docs
# (then --yes if it's still pre-push)
```

`--regenerate-docs` overwrites the three generated files. **It will overwrite manual edits to README.md / LICENSE / .gitignore** — if you've hand-edited any of them, copy your changes out first.

### "It says Path C — I have to do something manually"

Path C only fires if neither `gh` nor a cached PAT is available. The walkthrough is exact and short (about 5 steps in your browser + 1 command in your terminal). You can:

- **Now**: follow the walkthrough as printed (works immediately)
- **Later**: install `gh` and run `gh auth login` so future publishes go through Path A

### "I want to keep it private at first"

```bash
python3 scripts/publish.py /path/to/folder --private --yes
```

Flip to public later in GitHub Settings → General → Danger Zone → Change visibility.

### "I want a non-MIT license"

```bash
python3 scripts/publish.py /path/to/folder --license Apache-2.0
# or
python3 scripts/publish.py /path/to/folder --license GPL-3.0
```

If you don't know which one to pick, see [`references/license-chooser-newbie.md`](references/license-chooser-newbie.md). When in doubt, MIT.

### "I want to re-publish — there's already a commit"

If the project is already a git repo and there's nothing new to commit, Phase 5 prints "nothing new to commit (working tree clean)" and proceeds. If the GitHub repo doesn't exist yet, Phase 6 creates it and pushes. If the GitHub repo already exists and `origin` points there, you'll hit exit 4 — just run `git push -u origin main` yourself.

### "Scan flagged something that isn't actually a secret"

See the [`scan-ignore-file` marker](#scan-ignore-file-marker) section below. For a one-off false positive that you don't want to mark in the file, the only options are:

1. Reword the line so the regex doesn't match (e.g. add a space inside a fake-looking key string)
2. Move the example to a documentation-only file and add the marker to that file

There is intentionally no `--ignore-pattern` CLI flag — the failure mode of "user blanket-ignores a real leak" is too costly.

---

## Working with forks and third-party code

### If the project is a fork

If `git remote -v` includes an `upstream`, or your manifest file (`package.json`, `pyproject.toml`) says `forkedFrom`, Phase 2 marks it as a fork. Phase 3's attribution scan picks up the upstream URL. Phase 4 picks the `with-fork-attribution.md` README template, which contains placeholders at the top:

```
> This is a fork of [{UPSTREAM_NAME}]({UPSTREAM_URL}). Original work by {UPSTREAM_AUTHOR}.
```

You need to fill in the bracketed placeholders before push. The generator can detect the upstream URL but not the name/author — fill those manually.

**License compatibility**: a fork must retain the upstream's license. You can't fork a GPL project and re-publish as MIT. Phase 4 doesn't enforce this automatically; check yourself.

### If the project includes third-party code

If there's a `vendor/` / `third_party/` / `external/` / `deps/` directory, or any subdirectory with a `LICENSE` file, Phase 3 marks each one and Phase 4 picks the `with-acknowledgements.md` template. It generates an Acknowledgements section listing each location with `[需要你补全]` (needs filling) markers — you complete the original source URLs and authors before publishing.

The original LICENSE files in those subdirectories are **kept untouched** — Phase 4 only writes a top-level `LICENSE` for your own code.

---

## `scan-ignore-file` marker

Some files exist specifically to document patterns or recipes — e.g. a reference doc listing example secret strings, or a tutorial showing how to fix a leak. Those files will always self-match the scanner.

To tell `scan_project.py` to skip a file's content, put this marker anywhere in its first 2 KB:

```
<!-- scan-ignore-file: short reason -->
```

or in a Python file:

```python
# scan-ignore-file: short reason
```

The marker substring just has to appear; the comment style doesn't matter. The skill itself uses this on `scripts/scan_project.py` (which contains its own patterns), `scripts/generate_files.py` (docstring naturally says "based on"), and three reference docs.

**Use sparingly.** A marker says "trust this file's author to not paste real secrets here." Don't add it to source code that does real work — only to documentation about scanning.

---

## Customizing templates

All templates live under `references/`:

- `license-templates/{MIT,Apache-2.0,GPL-3.0}.txt` — canonical legal text with `{YEAR}` / `{COPYRIGHT_HOLDER}` placeholders
- `gitignore-templates/{python,node,shell,docs,general}.gitignore`
- `readme-templates/{basic,with-fork-attribution,with-acknowledgements}.md` — `{PLACEHOLDERS}` are substituted by `generate_files.py`

To add a new language gitignore: drop `your-language.gitignore` into `gitignore-templates/`, then add `"your-language": "your-language.gitignore"` to the `type_map` in `scripts/generate_files.py`.

To add a new license: drop `Your-License.txt` into `license-templates/` with `{YEAR}` and `{COPYRIGHT_HOLDER}` placeholders, then add the entry to `tmpl_map` in `generate_license()` of `scripts/generate_files.py`.

To customize the README structure: edit the template files. Placeholders are `{LIKE_THIS}`.

---

## Running each script directly

You don't have to use `publish.py`. Each phase script is callable on its own:

```bash
# Phase 1: Preflight
python3 scripts/preflight.py

# Phase 2: Detect
python3 scripts/detect_project_type.py /path/to/folder

# Phase 3: Scan
python3 scripts/scan_project.py /path/to/folder
# add --format json for machine-readable output

# Phase 4: Generate
python3 scripts/generate_files.py /path/to/folder \
    --name my-tool --author xiaomoBoy \
    --license MIT --type python \
    --description "..." --tested-on "macOS and Windows"

# Phase 5 (your job): git init, git add, git commit
# Phase 4.5: check_git_config (called from publish.py, can also run standalone)
python3 scripts/check_git_config.py /path/to/folder

# Phase 6: Create + push
python3 scripts/create_repo_safe.py /path/to/folder --name my-tool --public

# Phase 7: Verify
python3 scripts/verify_remote.py /path/to/folder
```

Each script's `--help` lists its full flag set.
