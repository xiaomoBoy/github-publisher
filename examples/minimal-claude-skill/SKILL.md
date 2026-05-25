---
name: greet
description: Use when the user wants to say hello. Calls scripts/greet.py to print a friendly greeting. Triggers on "say hi", "greet me", "hello".
---

# greet

A toy skill. Run `python3 scripts/greet.py` to get a greeting.

This exists as an example of the minimum a Claude-style skill needs:

- A frontmatter block with `name:` and `description:`
- A short body describing what to do

Real skills usually also have `references/` for doc data and more scripts. See `github-publisher` itself for a realistic example.
