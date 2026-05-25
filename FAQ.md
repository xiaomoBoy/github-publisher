# FAQ

中文版 → [FAQ.zh.md](FAQ.zh.md)

Common questions, in plain English. Each answer links to longer docs when needed.

- [Do I need to know `git` to use this?](#do-i-need-to-know-git-to-use-this)
- [Do I need an AI assistant?](#do-i-need-an-ai-assistant)
- [Will my real email show up on every commit?](#will-my-real-email-show-up-on-every-commit)
- [What if I want to delete the repo later?](#what-if-i-want-to-delete-the-repo-later)
- [Public or Private — which should I pick?](#public-or-private--which-should-i-pick)
- [MIT, Apache 2.0, or GPL — which license?](#mit-apache-20-or-gpl--which-license)
- [What happens if I accidentally push a secret?](#what-happens-if-i-accidentally-push-a-secret)
- [Does this tool cost money? Does it collect my code?](#does-this-tool-cost-money-does-it-collect-my-code)
- [Does this work on Linux?](#does-this-work-on-linux)
- [Can I use this offline?](#can-i-use-this-offline)
- [Why does Public default to MIT?](#why-does-public-default-to-mit)
- [Can I undo a publish?](#can-i-undo-a-publish)
- [Can I run this on a project that's already a git repo?](#can-i-run-this-on-a-project-thats-already-a-git-repo)

---

## Do I need to know `git` to use this?

**No.** The tool runs git commands for you (`init`, `add`, `commit`, `push`). It also handles GitHub auth via three fallback paths.

If something goes wrong, the tool prints exact commands to copy-paste — you don't need to type git commands from memory. [INSTALL.md](INSTALL.md) and [TROUBLESHOOTING.md](TROUBLESHOOTING.md) cover the few things you might run by hand (e.g. setting your name + email).

The one thing you must do once: set your git identity:

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

(Preflight reminds you with the exact command if you haven't.)

## Do I need an AI assistant?

**No.** AI is optional. With Claude Code (or similar), you say "open source `/path/to/project`" and the AI runs the scripts. Without AI, you run `python3 scripts/publish.py /path/to/project` yourself — same scripts, same flow.

The scripts are stdlib Python and work standalone. See [INSTALL.md § Standalone](INSTALL.md#standalone-no-ai).

## Will my real email show up on every commit?

**Yes, by default.** Whatever you put in `git config user.email` is stored in every commit, and the commit log is visible to anyone with the repo URL.

To keep your real email private, use GitHub's noreply alias:

1. Find your alias at <https://github.com/settings/emails>. It looks like `<id>+<username>@users.noreply.github.com`.
2. Set it:

   ```bash
   git config --global user.email "<your-username>@users.noreply.github.com"
   ```

`preflight.py` warns if your configured email looks like a personal address (gmail / outlook / qq / etc.) — but it never changes anything for you.

Full details: [INSTALL.md § Email privacy](INSTALL.md#email-privacy).

## What if I want to delete the repo later?

This tool deliberately won't delete a remote repo for you (too risky to automate). Two manual options:

```bash
# Via gh CLI — it makes you type the repo name to confirm
gh repo delete <owner>/<repo>
```

Or in the browser: open your repo → **Settings** → scroll to **Danger Zone** at the bottom → **Delete this repository**.

**Warning**: a deleted public repo can still be found via:
- Old caches in search engines or wayback-style archives
- Anyone who cloned or forked while it was up
- GitHub's own forking history (forks remain after deletion)

If the concern is a leaked secret, **revoking the secret at its source** (OpenAI / AWS / etc.) is more important than deleting the repo. See [TROUBLESHOOTING.md § I accidentally pushed a secret](TROUBLESHOOTING.md#i-accidentally-pushed-a-secret).

## Public or Private — which should I pick?

**Default Public** for a first-time open-source project. Reasons:

- "Open source" by definition is public
- Public repos get GitHub Issues, Discussions, Pages, free CI minutes, and indexing in search
- If you change your mind, flip in **Settings → Danger Zone → Change visibility**

**Private** makes sense if you want to test the publish flow first, share with specific people, or you're not sure the code is ready. Use `--private`:

```bash
python3 scripts/publish.py /path/to/folder --private
```

## MIT, Apache 2.0, or GPL — which license?

**90% of first-time projects: MIT.** It's the simplest, most permissive, and most familiar.

Quick decision tree:

| You care about | Pick |
|---|---|
| Don't know / don't care, just want a license | **MIT** |
| Worried a big company might use your code and sue you for patents | Apache 2.0 |
| Want anyone who modifies your code to also open-source theirs ("share-alike") | GPL 3.0 |
| Want to release into public domain — no attribution required | Unlicense / CC0 (rarely chosen) |

Detailed reasoning in [`references/license-chooser-newbie.md`](references/license-chooser-newbie.md).

Override with `--license`:

```bash
python3 scripts/publish.py /path/to/folder --license Apache-2.0
```

## What happens if I accidentally push a secret?

The tool's scanner refuses to publish if it finds a known-pattern secret (OpenAI keys, GitHub PATs, AWS keys, PEM private keys, etc.). It's designed to catch the most common leaks **before** they happen.

If you somehow get a real leak onto GitHub (e.g. the scanner missed a custom token format, or you `--skip-preflight` and ignored warnings):

1. **Revoke the leaked secret immediately** at its source (OpenAI dashboard / GitHub settings / AWS IAM / etc.). This is the most important step.
2. Generate a new secret, update your local config.
3. Optionally rewrite git history with [`git-filter-repo`](https://github.com/newren/git-filter-repo) or [BFG](https://rtyley.github.io/bfg-repo-cleaner/) — but understand that GitHub may cache the leaked commit, and anyone who cloned before your force-push still has it.

Full details: [TROUBLESHOOTING.md § I accidentally pushed a secret](TROUBLESHOOTING.md#i-accidentally-pushed-a-secret), [SECURITY.md](SECURITY.md).

## Does this tool cost money? Does it collect my code?

**No** to both.

- It's free and open source (MIT). No subscription, no signup, no paid tier.
- It runs entirely on your machine. The only network calls it makes are:
  - `api.github.com` — to check connectivity (preflight) and create the repo (Phase 6, only if you confirm push)
  - `github.com` — for the actual `git push` (Phase 6, only if you confirm push)
- It doesn't phone home, doesn't track usage, doesn't send your code anywhere except the GitHub repo **you explicitly create**.
- The Anthropic / OpenAI / etc. AI assistant you're using to drive it may have its own data policy — that's separate. The publishing scripts themselves don't talk to any AI service.

## Does this work on Linux?

**Probably yes, but it's not in the test matrix.** All scripts use Python stdlib + standard `git` / `gh` commands, so there's no reason it shouldn't work. The shipped tests pass on macOS and Windows. If you try it on Linux and something breaks, please open an issue.

## Can I use this offline?

**Partially.**

- Phase 1 (preflight) — checks `api.github.com` connectivity, so it'll warn if you're offline
- Phases 2, 3, 4, 5 — fully local; no network needed
- Phase 6 (create + push) — needs `github.com` + `api.github.com` reachable
- Phase 7 (verify) — needs `github.com` for `git fetch`

If you're offline, you can run up to Phase 5 (use `--no-push`) to generate the files and make the local commit. Push later when you have network.

```bash
python3 scripts/publish.py /path/to/folder --no-push
# Later, when online:
python3 scripts/publish.py /path/to/folder --yes
```

## Why does Public default to MIT?

Two layers of "least surprising for a first-timer":

- **Public**: this is an "open source" tool. The expectation is publishing publicly. If we defaulted Private, the name would be misleading.
- **MIT**: the most common, simplest license. No paragraphs of legalese, no patent / copyleft nuances. The license most likely to *not* cause downstream legal questions for either you or your users.

Both are one CLI flag away. The defaults are advisory, not opinionated.

## Can I undo a publish?

**Locally, yes**:

```bash
cd /path/to/folder
rm -rf .git LICENSE README.md .gitignore
```

This undoes Phase 4–5. Your source code was never touched.

**Remotely**: see [§What if I want to delete the repo later](#what-if-i-want-to-delete-the-repo-later) above. The remote delete is manual and may not erase caches / forks.

## Can I run this on a project that's already a git repo?

**Yes.** The tool detects an existing `.git/` and skips `git init`. If there's nothing new to commit (working tree clean), Phase 5 says "nothing new to commit" and proceeds to push if you `--yes`.

What it **won't** do automatically: pushing to an `origin` you already configured to a different URL. Phase 6 has a safety check that exits 4 if `origin` points somewhere unexpected. The error message gives you three options including a `--force-overwrite-origin` flag.

If you just want to push an already-set-up repo, you can skip this tool and run `git push -u origin main` yourself.

---

Question not here? Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md) or open an issue at <https://github.com/xiaomoBoy/github-publisher/issues>.
