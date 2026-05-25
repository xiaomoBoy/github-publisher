# Troubleshooting

中文版 → [TROUBLESHOOTING.zh.md](TROUBLESHOOTING.zh.md)

Find your error message below by searching (Ctrl/Cmd-F). Each entry has: **what it means** → **how to fix it**.

- [Install / environment](#install--environment)
- [Auth (gh / PAT / SSH)](#auth-gh--pat--ssh)
- [Push errors](#push-errors)
- [Scan errors / false positives](#scan-errors--false-positives)
- [Network / proxy](#network--proxy)
- [Skill not triggering in AI assistant](#skill-not-triggering-in-ai-assistant)
- [Tool / phase-specific](#tool--phase-specific)
- [Reset / recover](#reset--recover)

---

## Install / environment

### `git: command not found` / `'git' is not recognized`

**Means**: git isn't installed or isn't on `PATH`.

**Fix**:

```bash
# macOS
brew install git

# Windows PowerShell
winget install --id Git.Git
# Then open a NEW PowerShell window
```

### `python3: command not found` (Windows)

Windows installers sometimes only register `python` (not `python3`). Try `python --version`. If that works, use `python` everywhere the docs say `python3`.

Or, install from <https://python.org/downloads> and check **"Add Python to PATH"** during install.

### `Python 2.x` shows when running `python3`

Some old setups alias `python3` to Python 2. Check:

```bash
python3 -V
```

If it says 2.x, you need to install a current Python 3 (`brew install python@3.11` on macOS, or the installer on Windows).

### `[X ] git.user.name` / `[X ] git.user.email` in preflight

You haven't set a git identity. Set one (global so all repos use it):

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

Or use a GitHub noreply alias to keep your real email private — see [INSTALL.md § email privacy](INSTALL.md#email-privacy).

---

## Auth (gh / PAT / SSH)

### `gh: command not found`

**Means**: `gh` CLI isn't installed. It's optional — the tool falls back to Path B (PAT) or Path C (manual).

**Fix** (if you want Path A):

```bash
# macOS
brew install gh

# Windows
winget install --id GitHub.cli
```

After install: `gh auth login`.

### `gh auth status` shows "You are not logged into any GitHub hosts"

```bash
gh auth login
```

Choose: `GitHub.com` → `HTTPS` → `Yes (authenticate Git)` → `Login with a web browser`.

### `Authentication failed for 'https://github.com/...'`

**Means**: HTTPS push tried to use a password, but GitHub doesn't accept passwords anymore. You need a Personal Access Token (PAT).

**Fix**:

1. Generate: <https://github.com/settings/tokens/new>
2. Scopes: tick `repo`
3. Click **Generate token** — **copy it immediately** (you cannot view it again later)
4. Re-run `git push`. When prompted for username, enter your GitHub login. When prompted for password, **paste the PAT**.
5. To remember it next time, configure a credential helper:

   ```bash
   # macOS
   git config --global credential.helper osxkeychain
   # Windows
   git config --global credential.helper manager
   ```

### `Permission denied (publickey)` on `git push`

**Means**: you're using an SSH remote URL, but your SSH key isn't recognized by GitHub.

**Fastest fix**: switch the remote to HTTPS:

```bash
git remote set-url origin https://github.com/<your-username>/<repo>.git
git push -u origin main
```

It will prompt for a username + password (use a PAT for the password).

**Proper fix**: generate an SSH key and add to GitHub:

```bash
ssh-keygen -t ed25519 -C "you@example.com"
# accept defaults (Enter through prompts, no passphrase if you prefer)

# macOS / Linux
cat ~/.ssh/id_ed25519.pub

# Windows PowerShell
Get-Content $env:USERPROFILE\.ssh\id_ed25519.pub
```

Copy the output, then add at <https://github.com/settings/keys> → **New SSH key**.

### Preflight says `git.credential` is `warning: No PAT cached`

That just means Path B isn't currently usable. If Path A (`gh`) is OK, you don't need to do anything. If you want Path B specifically:

1. Generate a PAT (see above)
2. Set a credential helper (see above)
3. Run any `git fetch` / `git push` against a private repo — git will prompt and cache the PAT

---

## Push errors

### `Updates were rejected because the remote contains work that you do not have locally`

**Means**: the GitHub repo already has commits you don't have locally. Usually happens when you ticked "Add README" while creating the repo on the web.

**Fix**:

```bash
git pull origin main --rebase
git push -u origin main
```

If conflicts pile up, the simplest is to **delete the repo on GitHub** and recreate without ticking any boxes.

### `fatal: remote origin already exists`

**Means**: `origin` was already configured before. `publish.py` Phase 6 has a safety check that exits with code 4 if `origin` points somewhere else — see the section below.

If you just need to change it manually:

```bash
git remote set-url origin <new-url>
```

### `exit 4` from `publish.py` / `create_repo_safe.py`

Means: `origin` is configured to a different URL than the one we'd push to. Tool refuses to silently overwrite. Three options (in the printed hint):

1. **Already pointing where you want?** Just `git push -u origin main` manually.
2. **Want to replace?** `python3 scripts/create_repo_safe.py … --force-overwrite-origin`
3. **Want to start over?** `git remote remove origin`, then re-run `publish.py`

### `remote: error: File X is XX MB; this exceeds GitHub's file size limit`

**Means**: a file > 100 MB in a commit. GitHub rejects it.

**Fix**:

```bash
# 1. Add it to .gitignore
echo "<path>" >> .gitignore

# 2. Untrack
git rm --cached <path>
git commit -m "Stop tracking large file"
git push -u origin main
```

If the large file is already in a commit (not just staged), you need to rewrite history:

```bash
pip install git-filter-repo
git filter-repo --invert-paths --path <path>
git push --force-with-lease
```

`--force-with-lease` (not `--force`) is the safer option — it won't overwrite remote work you haven't seen yet.

For large files you genuinely want to track, use [Git LFS](https://git-lfs.github.com/).

---

## Scan errors / false positives

### Scan flags an example string in my documentation file

The file is documenting patterns or recipes — by design it contains things that look like secrets.

**Fix**: add a `scan-ignore-file` marker in the file's first 2 KB:

```
<!-- scan-ignore-file: this is a reference doc that intentionally lists example patterns -->
```

or in Python:

```python
# scan-ignore-file: pattern source self-matches
```

See [USAGE.md § scan-ignore-file marker](USAGE.md#scan-ignore-file-marker) for when this is and isn't appropriate.

### Scan flags a real secret I committed by accident

The fix has two parts:

1. **Stop the bleeding**: remove the secret from your working tree per [`references/secret-fix-recipes.md`](references/secret-fix-recipes.md). Then re-run scan to verify GREEN.

2. **Revoke the secret**: even if you delete from the next commit, the leaked value is **already in git history** (and any clone someone made). You MUST go to the service (OpenAI / GitHub / AWS / etc.) and **revoke the leaked token, generate a new one**.

This tool does not rewrite git history — see [SECURITY.md](SECURITY.md). For history rewriting, use [`git-filter-repo`](https://github.com/newren/git-filter-repo) or [BFG](https://rtyley.github.io/bfg-repo-cleaner/), but understand that already-pushed history may live in GitHub caches / forks even after rewriting.

### Scan keeps flagging the same thing even after I removed it

Three possibilities:

1. **You didn't save the file** before re-running scan. Save, then re-run.
2. **The secret is in another file** with similar content. Look at the `file:line` in the scan output carefully.
3. **The secret is in git history**, but the scan only looks at the working tree. The current working-tree fix is enough to stop further leakage, but the historical leak still exists in commits — handle per the previous question.

### Scan reports `attribution_comments` but I don't have third-party code

Did the scanner pick up a code comment that incidentally says "based on" / "inspired by" / "@author"? This only scans files with code extensions (`.py`, `.js`, `.rs`, etc.), so something in your code matches. Either:

- Reword the comment if it doesn't actually mean attribution
- Add `scan-ignore-file` marker to the file (only if the file is reference / template documentation)

---

## Network / proxy

### `Could not resolve host: github.com`

**Means**: DNS or network is broken.

**Diagnose**:

```bash
ping github.com
curl -v https://github.com
```

If you use a proxy:

```bash
git config --global http.proxy http://127.0.0.1:7890
git config --global https.proxy http://127.0.0.1:7890
```

(Replace `7890` with your proxy port.)

When done, unset:

```bash
git config --global --unset http.proxy
git config --global --unset https.proxy
```

### `network.github` shows `cannot reach api.github.com` in preflight

Same as above. The tool reaches `api.github.com` for repo creation and `github.com` for git push. Both must be reachable.

If you're in a region where GitHub access is unstable, consider using a VPN or proxy.

### `SSL: CERTIFICATE_VERIFY_FAILED`

**Means**: your Python install's CA bundle is broken.

**macOS fix** (after Python.org install):

```bash
/Applications/Python\ 3.11/Install\ Certificates.command
```

Or:

```bash
pip install --upgrade certifi
```

---

## Skill not triggering in AI assistant

### "I said 'open source XX' but the AI didn't run the skill"

**Check**:

1. Skill directory exists at `~/.claude/skills/github-publisher/` (or your client's expected path)
2. The directory contains `SKILL.md` at its root
3. You restarted the AI client after installing
4. Your trigger phrase is recognizable — try one of:
   - "open source `/path/to/project`"
   - "publish this folder to GitHub"
   - "把这个项目推到 GitHub"
   - "create a public GitHub repo from `<path>`"

For Claude Code specifically: skills are loaded on session start. Restart the CLI / IDE extension.

### "AI started but ran the wrong commands"

If you see the AI typing custom `git` commands instead of calling `python3 scripts/publish.py`, the skill wasn't loaded. Verify the directory:

```bash
ls ~/.claude/skills/github-publisher/
# should show: LICENSE  README.md  SKILL.md  references/  scripts/  ...
```

### "AI ran preflight but ignored its output"

Open SKILL.md and check that it's not been corrupted (e.g. truncated YAML frontmatter). The `name:` and `description:` lines must be intact, and the file must start with `---`.

---

## Tool / phase-specific

### `exit 10` — preflight not ready

Required tool is missing or unconfigured. The preflight output above the exit will tell you exactly which and how to fix. Most common: git not installed, or `git config user.email` unset.

### `exit 11` — scan RED

A real or apparent secret / private path / sensitive file was detected. The scan output lists each finding with its location and fix hint. Resolve per [`references/secret-fix-recipes.md`](references/secret-fix-recipes.md) and re-run.

### `exit 12` — pre-push review

**Not an error.** This is the explicit checkpoint before push. Read the printed plan; if everything looks right, re-run the same command with `--yes`.

### `exit 13` — fell through to Path C (manual)

Neither `gh` nor a cached PAT is available. Follow the printed walkthrough — it's a few steps in your browser + one terminal command. Or set up `gh` / a PAT and re-run (see [INSTALL.md § Step 4](INSTALL.md#step-4--configure-github-auth)).

### `publish.py` hangs at Phase 6

`git push` may be waiting on credential input. Run the same `git push -u origin main` manually in another terminal — if it prompts for credentials, supply them and let git cache them (then re-run `publish.py`).

### Phase 4 shows `[skip]` for everything

The three files (`README.md`, `LICENSE`, `.gitignore`) already exist and the tool defaults to skipping (so it doesn't overwrite manual edits). If you want to regenerate (e.g. because you changed `--description`):

```bash
python3 scripts/publish.py /path/to/folder --description "..." --regenerate-docs
```

---

## Reset / recover

### "I want to undo everything publish.py did locally"

```bash
cd /path/to/folder
rm -rf .git LICENSE README.md .gitignore
```

This puts the folder back to before Phase 4–5. (Your source code was never touched.)

### "I want to delete the GitHub repo I just created"

This tool deliberately won't do that for you — it's a destructive operation against a remote system.

```bash
# Via gh CLI (you'll be asked to confirm by typing the repo name)
gh repo delete <owner>/<repo>

# Or via the web: Settings → General → Danger Zone → Delete this repository
```

### "I accidentally pushed a secret"

1. Immediately go to the service (OpenAI / GitHub / AWS / etc.) and **revoke the leaked token**. This is the most important step.
2. Generate a new token and update your local config to use it.
3. Optionally rewrite git history with `git-filter-repo` or BFG, then `git push --force-with-lease`. **But understand**: GitHub may cache the leaked commit, and anyone who cloned before your force-push still has the old history.
4. The "real" remediation is always #1. Don't skip it because you "fixed" git history.

See [`references/secret-fix-recipes.md § git history`](references/secret-fix-recipes.md) for more.

---

If your problem isn't here, please open an issue: <https://github.com/xiaomoBoy/github-publisher/issues>. Include:
- the exact command you ran
- the full output (redact any secrets)
- your OS and `python3 --version`
- whether preflight passed
