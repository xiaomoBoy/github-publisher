# Install

中文版 → [INSTALL.zh.md](INSTALL.zh.md)

This guide covers:
- [Prerequisites](#prerequisites)
- [Step 1 — Install on macOS](#step-1--install-on-macos)
- [Step 1 — Install on Windows](#step-1--install-on-windows)
- [Step 2 — Place the skill](#step-2--place-the-skill)
- [Step 3 — Verify with preflight](#step-3--verify-with-preflight)
- [Step 4 — Configure GitHub auth](#step-4--configure-github-auth)
- [Per-AI-client setup](#per-ai-client-setup)
- [Standalone (no AI)](#standalone-no-ai)
- [Uninstall](#uninstall)

---

## Prerequisites

Required:

- **Python 3.8+** (3.10+ recommended). Stdlib only — no `pip install` needed.
- **git** 2.x or newer
- A **GitHub account** (free is fine)
- Network access to `api.github.com` and `github.com`

Optional (smoother experience, but not required):

- **`gh` CLI** — enables the most automated auth path (Path A). Without it, the tool falls back to `git credential` (Path B) or a manual web walkthrough (Path C).

If you skip both `gh` and `git credential`, you can still publish — Path C just prints the exact commands to run by hand.

---

## Step 1 — Install on macOS

```bash
# Already have these? Skip the lines you have.
brew install git python@3.11
brew install gh             # optional, but recommended
```

Verify:

```bash
git --version       # git version 2.x
python3 --version   # Python 3.x
gh --version        # gh version 2.x   (optional)
```

If `brew` itself is missing, install it from <https://brew.sh>.

---

## Step 1 — Install on Windows

Use **PowerShell** (not `cmd.exe`).

```powershell
# Already have these? Skip the lines you have.
winget install --id Git.Git
winget install --id Python.Python.3.11
winget install --id GitHub.cli       # optional, but recommended
```

After install, **open a new PowerShell window** so `PATH` updates take effect.

Verify:

```powershell
git --version
python --version       # may be `python3` depending on install
gh --version           # optional
```

If `python` doesn't exist but `python3` does, replace `python` with `python3` everywhere in the docs.

> Tip — Use Git Bash if you prefer a unix-style shell. It ships with Git for Windows. All commands in these docs work in both PowerShell and Git Bash.

---

## Step 2 — Place the skill

The skill is a single directory. Where you put it depends on how you'll use it.

### If you use Claude Code

```bash
# macOS / Linux / Git Bash
git clone https://github.com/xiaomoBoy/github-publisher.git ~/.claude/skills/github-publisher
```

```powershell
# Windows PowerShell
git clone https://github.com/xiaomoBoy/github-publisher.git $env:USERPROFILE\.claude\skills\github-publisher
```

Claude Code auto-loads skills from `~/.claude/skills/` on next launch.

### If you use another AI tool with skill support

Place the directory where that tool expects skills, then load it per its own docs. The skill is just a folder with `SKILL.md` at the root.

### If you want it standalone (no AI)

Clone anywhere, then run the scripts directly:

```bash
git clone https://github.com/xiaomoBoy/github-publisher.git
cd github-publisher
python3 scripts/preflight.py
```

---

## Step 3 — Verify with preflight

`preflight.py` checks every prerequisite and tells you exactly what's missing (with the install command for your OS):

```bash
python3 ~/.claude/skills/github-publisher/scripts/preflight.py
```

A passing run looks like:

```
=== Preflight (macOS) ===

  [OK] python3                 Python 3.12.7
  [OK] git                     git version 2.52.0
  [OK] git.user.name           xiaomoBoy
  [OK] git.user.email          46080225+xiaomoBoy@users.noreply.github.com
  [OK] gh                      gh version 2.92.0          (optional)
  [OK] gh.auth                 Logged in to github.com    (optional)
  [OK] git.credential          PAT available              (optional)
  [OK] network.github          api.github.com HTTP 200

Available auth paths: A (gh CLI), B (API via git credential), C (manual web walkthrough)
Ready to publish.
```

If something shows `[X ]` (required missing) or `[!!]` (required needs setup), preflight prints the exact command to fix it. **You don't have to memorize anything — just copy the suggested command and re-run preflight until it's all green.**

Things marked `[~ ]  (optional)` won't block publishing. They just unlock a smoother path.

### Common preflight outcomes

| Symptom | Meaning | Fix |
|---|---|---|
| `[X ] git` | git not installed | Run the `brew install git` / `winget install --id Git.Git` shown |
| `[!!] git.user.name` | Never set your name | `git config --global user.name "Your Name"` |
| `[!!] git.user.email` | Never set your email | `git config --global user.email "you@example.com"` (or noreply, see below) |
| `[X ] network.github` | Can't reach `api.github.com` | Check VPN / proxy / firewall |

---

## Step 4 — Configure GitHub auth

The tool tries three auth paths in order. **You only need ONE of them to work.**

### Path A — `gh` CLI (recommended; most automated)

```bash
gh auth login
```

Choose:
- `GitHub.com`
- `HTTPS`
- `Yes` (authenticate Git with your GitHub credentials)
- `Login with a web browser`

After the browser flow, you'll be logged in. Verify:

```bash
gh auth status
```

### Path B — `git credential` (PAT cached in OS keychain)

If you don't want `gh` CLI, you can let git cache a Personal Access Token (PAT) in your OS keychain. The tool reads the token via `git credential fill` — it never touches plain text.

1. Generate a PAT: <https://github.com/settings/tokens/new>
2. Set:
   - **Note**: any label (e.g. "my-laptop")
   - **Expiration**: `90 days` or `No expiration`
   - **Scopes**: `repo` (only one needed)
3. Click **Generate token**, copy it immediately
4. Set up a credential helper so git can remember it:
   - macOS: `git config --global credential.helper osxkeychain`
   - Windows: `git config --global credential.helper manager`
5. On your first `git push`, git will prompt for username + password. Username is your GitHub login, **password is the PAT** you just generated. It gets saved.

After that, `git credential fill` will return the cached PAT silently and the tool uses Path B.

### Path C — Manual web walkthrough (no auth needed)

If neither Path A nor B is available, `publish.py` will fall through to Path C: it prints exact commands and a step-by-step web walkthrough to create the repo manually. You'll need to:

1. Open <https://github.com/new>
2. Fill in the repo name (the walkthrough tells you which)
3. Do **not** check Add README / .gitignore / license boxes (we already generated those locally)
4. Click **Create repository**
5. Run the `git remote add origin ... && git push -u origin main` commands the walkthrough printed

Path C always works as long as you have a GitHub account and a browser.

### Email privacy

By default `git commit` records the email you set in `git config user.email`, and **every commit's email is visible to anyone with the repo URL**.

To keep your real email private, use GitHub's noreply alias:

1. Find your alias at <https://github.com/settings/emails>. Format is `<id>+<username>@users.noreply.github.com` (or just `<username>@users.noreply.github.com` for older accounts).
2. Set it:

   ```bash
   git config --global user.email "<your-username>@users.noreply.github.com"
   ```

`preflight.py` and `check_git_config.py` will softly remind you if your configured email looks like a personal address (gmail / outlook / etc.) — they never change it, just warn.

---

## Per-AI-client setup

### Claude Code (CLI / web / IDE)

After `git clone` into `~/.claude/skills/github-publisher/`, restart Claude Code. The skill is auto-discovered.

Trigger it by saying:

- "open source `/path/to/my-project`"
- "把这个项目推到 GitHub"
- "publish this folder"

Claude reads `SKILL.md`, follows Quick Mode (preflight → publish.py), and only asks you 1–2 yes/no questions (install missing tools? push?).

### Cursor / other AI editors

If the editor supports loading skills from a directory, point it at `~/.claude/skills/github-publisher/`. The trigger phrases are the same.

### Copilot CLI / Gemini CLI

If they support `SKILL.md`-style skills, place the directory at the path they expect. Otherwise treat the tool as standalone (next section).

### "I just want to run the scripts"

The whole tool is `scripts/*.py`. You don't need any AI at all — see the next section.

---

## Standalone (no AI)

You can drive `publish.py` directly. Recommended workflow:

```bash
# Quick env check (informational, exits 0 if ready)
python3 scripts/preflight.py

# Dry run: stops after Phase 5 with a printed plan, exit code 12
python3 scripts/publish.py /path/to/my-project \
    --name my-tool \
    --description "One line about it" \
    --license MIT \
    --public

# Inspect the plan it printed, then:
python3 scripts/publish.py /path/to/my-project \
    --name my-tool \
    --description "One line about it" \
    --license MIT \
    --public \
    --yes
```

The `--yes` flag is the explicit push confirmation. Without it, `publish.py` never pushes (Hard Constraint #2).

Full flag reference is in [USAGE.md](USAGE.md).

---

## Uninstall

```bash
# macOS / Linux
rm -rf ~/.claude/skills/github-publisher

# Windows PowerShell
Remove-Item -Recurse -Force $env:USERPROFILE\.claude\skills\github-publisher
```

That's it. The tool writes nothing outside its own directory and the target project being published. It doesn't install anything to your global Python.

If you set up a credential helper or generated a PAT specifically for this tool, you can revoke them at:
- <https://github.com/settings/tokens> (revoke PAT)
- `git config --global --unset credential.helper` (remove helper)
