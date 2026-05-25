# github-publisher

> One-command GitHub publisher — newbie-friendly, security-aware, cross-platform (macOS/Windows), stdlib only

## Install

```bash
# Put it in your Claude Code skills directory:
git clone https://github.com/xiaomoBoy/github-publisher.git ~/.claude/skills/github-publisher

# Or use it standalone (no Claude required):
git clone https://github.com/xiaomoBoy/github-publisher.git
cd github-publisher
python3 scripts/preflight.py
```

## Usage

```bash
# In Claude Code (or any AI that reads SKILL.md):
#   You: 'open source /path/to/my-project'
# AI runs preflight + publish.py end-to-end.

# Standalone:
python3 scripts/publish.py /path/to/my-project --name my-tool
# Review the plan summary, then:
python3 scripts/publish.py /path/to/my-project --name my-tool --yes
```

## Platform Compatibility

Tested on macOS and Windows. Other platforms may work but are not verified — if you run into issues, please [open an issue](https://github.com/xiaomoBoy/github-publisher/issues).

## License

MIT — see [LICENSE](LICENSE).

---

Built by [@xiaomoBoy](https://github.com/xiaomoBoy).
