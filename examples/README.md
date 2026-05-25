# Example projects

Each subdirectory here is a tiny self-contained project you can use to try out `github-publisher` **without risking your real code**.

| Folder | What's in it | Try it with |
|---|---|---|
| [`minimal-python/`](minimal-python/) | A 5-line Python tool with no LICENSE / README / .gitignore | `publish.py examples/minimal-python --dry-run` |
| [`minimal-claude-skill/`](minimal-claude-skill/) | A skeleton Claude skill (`SKILL.md` + one Python script) | `publish.py examples/minimal-claude-skill --dry-run` |
| [`with-secrets-fail-demo/`](with-secrets-fail-demo/) | A project that **intentionally contains a fake OpenAI key** — used to demo the scanner refusing to publish | `publish.py examples/with-secrets-fail-demo --dry-run` (expect exit 11) |

## How to use

1. **First time?** Start with `minimal-python`:

   ```bash
   cd /path/to/github-publisher
   python3 scripts/publish.py examples/minimal-python --dry-run
   ```

   `--dry-run` is zero-side-effect: it runs preflight / detect / scan and prints the plan, but **does not** write any files, `git init`, or commit. Use it to see what the full publish flow would do, safely.

2. **Want to see the scanner refuse?** Try `with-secrets-fail-demo`:

   ```bash
   python3 scripts/publish.py examples/with-secrets-fail-demo --dry-run
   # exits 11 (scan RED) and prints the leaked-secret location + fix hint
   ```

3. **When you're comfortable, run on your real project**:

   ```bash
   python3 scripts/publish.py /path/to/your/project --dry-run     # safe preview
   python3 scripts/publish.py /path/to/your/project               # actually generates files + commits locally; stops at pre-push review
   python3 scripts/publish.py /path/to/your/project --yes         # actually pushes to GitHub
   ```

## Don't publish the examples to GitHub

These are samples for trying the tool. They're not interesting on their own. If you want to push one of them up to "see what shows up on GitHub," create a throwaway repo on your account that you can delete after.
