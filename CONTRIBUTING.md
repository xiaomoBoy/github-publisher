# Contributing

Thanks for considering a contribution! This document covers:

- [Project scope (what we accept, what we don't)](#project-scope)
- [Dev setup](#dev-setup)
- [Code style](#code-style)
- [Running tests](#running-tests)
- [Adding a new license template](#adding-a-new-license-template)
- [Adding a new .gitignore template](#adding-a-new-gitignore-template)
- [Adding a new README template](#adding-a-new-readme-template)
- [Modifying the scanner](#modifying-the-scanner)
- [Modifying the orchestrator (`publish.py`)](#modifying-the-orchestrator-publishpy)
- [PR checklist](#pr-checklist)

---

## Project scope

This is a focused tool with deliberate constraints. **In scope**:

- Improvements to the 6 scripts in `scripts/`
- New / better templates in `references/`
- Bug fixes
- Docs improvements (README / INSTALL / USAGE / TROUBLESHOOTING / SECURITY)
- Cross-platform fixes (especially Linux validation)
- New language `.gitignore` templates
- More accurate / less false-positive scan patterns

**Out of scope** (please don't PR these):

- Anything that modifies user source code automatically (we only write `README.md` / `LICENSE` / `.gitignore`)
- Anything that rewrites git history
- Anything that changes GitHub repo settings on behalf of the user
- New CLI flags that silently bypass the `--yes` push gate
- Heavy dependencies (we're stdlib only, period)
- A web UI / desktop app — the tool is meant to be embedded in AI assistants and tooling, not to grow its own UI

If you're not sure whether something is in scope, open an issue first to discuss.

---

## Dev setup

```bash
git clone https://github.com/xiaomoBoy/github-publisher.git
cd github-publisher

# All scripts are stdlib Python 3.8+. No `pip install` needed.
# Sanity:
python3 scripts/preflight.py
python3 -m py_compile scripts/*.py
```

That's it. No virtualenv, no `requirements.txt`, no build step.

---

## Code style

- Python: PEP 8 with relaxed line length (~100 chars). Don't add a linter to CI; just be consistent.
- `from __future__ import annotations` at the top of every script (we target 3.8+ but use modern type-hint syntax).
- Stdlib only. No `requests`, no `click`, no `rich`. If you find yourself wanting one, ask in an issue first.
- Top-of-file docstring explains what the script does and how it's called.
- Each script should be runnable on its own (`python3 scripts/<name>.py --help` should work) and also importable / composable from `publish.py`.
- Functions that need git: subprocess directly, no `gitpython` or similar. See existing scripts for patterns.

---

## Running tests

There is currently no automated test suite (the project is small and the tests would be mostly integration tests against real GitHub). The expected manual smoke test before any PR:

```bash
# 1. Syntax
python3 -m py_compile scripts/*.py

# 2. Preflight (should pass on your machine)
python3 scripts/preflight.py

# 3. End-to-end on a throwaway folder
rm -rf /tmp/contrib-test && mkdir /tmp/contrib-test
echo 'print("hi")' > /tmp/contrib-test/main.py
python3 scripts/publish.py /tmp/contrib-test --description "smoke" 
# Expect: exits 12 with Pre-push review

# 4. Negative case: red scan
echo 'KEY = "sk-proj-AAAABBBBCCCCDDDDEEEEFFFF"' > /tmp/contrib-test/bad.py
python3 scripts/publish.py /tmp/contrib-test
# Expect: exits 11 with RED

# 5. Cleanup
rm -rf /tmp/contrib-test
```

If you change the scanner, also test against a few known patterns to confirm you didn't regress detection. Patterns documented in `references/private-data-patterns.md`.

---

## Adding a new license template

1. Get the canonical text from <https://choosealicense.com/licenses/> or the upstream source (apache.org / gnu.org).
2. Save to `references/license-templates/<SPDX-ID>.txt`.
3. Substitute the copyright placeholders with `{YEAR}` and `{COPYRIGHT_HOLDER}`. Look for things like `[yyyy]` / `<year>` / `[name of copyright owner]` / `<name of author>` in the canonical text.
4. Add a `tmpl_map` entry in `scripts/generate_files.py:generate_license()`:

   ```python
   tmpl_map = {
       "MIT": "license-templates/MIT.txt",
       "Apache-2.0": "license-templates/Apache-2.0.txt",
       "GPL-3.0": "license-templates/GPL-3.0.txt",
       "Your-SPDX-ID": "license-templates/Your-SPDX-ID.txt",  # add this
   }
   ```

5. Optionally update `references/license-chooser-newbie.md` with a one-liner explaining when to use it.

---

## Adding a new .gitignore template

1. Get the canonical template from <https://github.com/github/gitignore> (or write your own).
2. Save to `references/gitignore-templates/<language>.gitignore`.
3. Add to `type_map` in `scripts/generate_files.py:generate_gitignore()`:

   ```python
   type_map = {
       "python": "python.gitignore",
       # ...
       "<language>": "<language>.gitignore",  # add this
   }
   ```

4. Add the language to `EXTENSION_TYPES` and `MANIFEST_TYPES` in `scripts/detect_project_type.py` so auto-detection works:

   ```python
   MANIFEST_TYPES = [
       # ...
       ("<canonical-manifest-file>", "<language>"),
   ]

   EXTENSION_TYPES = {
       # ...
       ".<ext>": "<language>",
   }
   ```

5. Smoke-test against a real project of that language.

---

## Adding a new README template

Templates use `{LIKE_THIS}` placeholders. Available placeholders (substituted by `generate_files.py:generate_readme()`):

- `{PROJECT_NAME}`, `{ONE_LINE_DESCRIPTION}`
- `{AUTHOR}`, `{AUTHOR_URL}`
- `{LICENSE}`, `{LICENSE_FILE}`, `{REPO_URL}`
- `{TESTED_PLATFORMS}`, `{INSTALL_COMMAND}`, `{USAGE_EXAMPLE}`
- For fork attribution: `{UPSTREAM_NAME}`, `{UPSTREAM_URL}`, `{UPSTREAM_AUTHOR}`, `{UPSTREAM_LICENSE}`, `{WHY_FORK_OR_SHORT_DESCRIPTION}`, `{CHANGE_1}`, `{CHANGE_2}`
- For acknowledgements: `{ACKNOWLEDGEMENTS_LIST}`

Steps:

1. Write the template in `references/readme-templates/<name>.md`.
2. Edit `pick_readme_template()` in `scripts/generate_files.py` to choose your new template under the right conditions.
3. If you introduce new placeholders, populate them in `generate_readme()`.

---

## Modifying the scanner

`scripts/scan_project.py` is the most safety-critical script. Changes should:

- **Not weaken detection** — confirm each existing strong-pattern still matches its canonical example
- **Default to false-positive over false-negative** — better to flag something benign than miss a real secret
- **Respect the `scan-ignore-file` marker semantics** — don't add a way to disable the entire scan via CLI
- **Keep the output schema stable** — `publish.py` parses the JSON; breaking changes need to update both

When adding a new strong-pattern secret type:

1. Get an example from official docs (don't paste a real key)
2. Add to `STRONG_SECRET_PATTERNS` with a tight regex
3. Test against the example; test that random text doesn't match

When adding a new weak-pattern: it goes in `WEAK_SECRET_PATTERNS` and is reported as YELLOW.

---

## Modifying the orchestrator (`publish.py`)

`publish.py` is the user-facing entrypoint. Changes should:

- **Preserve exit-code contract** (0, 1, 4, 10, 11, 12, 13) — see [USAGE.md § Exit codes](USAGE.md#exit-codes). Adding new codes is OK; reassigning is not.
- **Keep phase ordering** — preflight → detect → scan → generate → git → (review) → create+push → verify
- **Never auto-pass `--yes`** — that's the user's job
- **Output format** — keep `--format human` parseable by humans and `--format json` parseable by AI orchestrators

For new flags: prefer composing existing scripts over moving logic into `publish.py`. Each phase script should remain independently useful.

---

## PR checklist

Before submitting:

- [ ] Read this CONTRIBUTING.md
- [ ] Ran `python3 -m py_compile scripts/*.py` — no errors
- [ ] Ran the manual smoke test above — pass
- [ ] If you touched the scanner: confirmed existing patterns still match their canonical examples
- [ ] If you added a new template / language: ran end-to-end against a real project of that type
- [ ] Updated relevant docs (README / INSTALL / USAGE / TROUBLESHOOTING / SECURITY) if user-visible behavior changed
- [ ] If user-visible CLI changed: updated both `USAGE.md` and `USAGE.zh.md`
- [ ] Added a `CHANGELOG.md` entry under `## [Unreleased]`
- [ ] Commit messages are descriptive (`Fix X by Y` not `update`, `wip`)

### PR scope

Smaller PRs are easier to review. If your change touches multiple unrelated things, please split them. A good PR addresses one issue or adds one feature.

### Style for commit messages

Imperative, ≤72 chars on the subject line, blank line, then body. Reference issues with `Fixes #N` if applicable.

```
Add support for Rust .gitignore template

- Adds references/gitignore-templates/rust.gitignore
- Maps `rust` type in generate_files.py
- Updates detect_project_type.py to pick up Cargo.toml

Fixes #42
```

---

## Code of conduct

Be kind. Assume good intent. We're all volunteers here.

If a maintainer is slow to respond, that's because we have day jobs — please be patient.
