# with-secrets-fail-demo

> This project **intentionally** contains a fake OpenAI API key in `config.py`. It exists so you can see what the scanner does when it finds a leaked secret.

The fake key isn't real (it's `sk-proj-` followed by a fixed dummy string), but it matches the scanner's strong-pattern regex for OpenAI keys, so `scan_project.py` will flag it as RED.

## Try it

```bash
python3 scripts/publish.py examples/with-secrets-fail-demo --dry-run
```

Expected output (abbreviated):

```
=== Phase 3 — Security + attribution scan ===
Status: RED
Strong secrets: 1

RED findings — must fix before publishing:
  - strong_secret/openai @ config.py:2
      preview: sk-pro...REDACTED...XXXX
      fix:     See references/secret-fix-recipes.md (search 'openai').

After fixing, re-run: python3 publish.py <path> ...
```

Exit code: `11`.

The point: `publish.py` will refuse to continue past the scan, so the fake key never reaches Phase 6 (push). This is the main safety guarantee — see [SECURITY.md](../../SECURITY.md).
