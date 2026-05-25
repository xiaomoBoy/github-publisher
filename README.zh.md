# github-publisher

> 一句话把本地项目开源到 GitHub —— `"开源 /path/to/my-project"`。
> 给第一次开源的人 / 非程序员用。带安全扫描。纯 Python 标准库。macOS + Windows。

English → [README.md](README.md)

---

## 这是什么

一个可复用的 AI skill（也是独立的 Python 工具），把本地文件夹安全地发布成 GitHub 公开仓库。适合：

- 没开源过项目，不想学 12 个命令的人
- 会 git 但每次都不想手写 `README` / `LICENSE` / `.gitignore` 的人
- 想要一个"二次审视"，**扫到 secret 就拒绝推送**

可以让 AI 助手驱动（"把这个文件夹开源"），也可以直接跑 Python 脚本。两种方式实际跑的是同一份脚本——AI 层只是 orchestrator，没"AI 魔法"。

## 快速开始

```bash
# 1. 装
git clone https://github.com/xiaomoBoy/github-publisher.git ~/.claude/skills/github-publisher

# 2. 体检环境
python3 ~/.claude/skills/github-publisher/scripts/preflight.py

# 3. 开源
#    通过 AI 助手（Claude Code 等）：
#      对话里说："开源 /path/to/my-project"
#    或独立运行：
python3 ~/.claude/skills/github-publisher/scripts/publish.py /path/to/my-project
# 看一下打印出的 plan，再带 --yes 重跑确认推送：
python3 ~/.claude/skills/github-publisher/scripts/publish.py /path/to/my-project --yes
```

详细文档：[INSTALL.zh.md](INSTALL.zh.md) · [USAGE.zh.md](USAGE.zh.md) · [TROUBLESHOOTING.zh.md](TROUBLESHOOTING.zh.md) · [SECURITY.zh.md](SECURITY.zh.md)

## 它做什么（7 个 phase）

| # | Phase | 跑什么 | 产出 |
|---|---|---|---|
| 1 | 环境自检 | `preflight.py` | 报告缺啥（git? gh? PAT?），附对应 OS 的安装命令 |
| 2 | 项目识别 | `detect_project_type.py` | 猜项目类型（Python / Node / Claude skill / ...） |
| 3 | 安全扫描 | `scan_project.py` | 三层扫：secret / 引用归属 / 大文件。RED ⇒ 拒绝继续 |
| 4 | 生成必备 | `generate_files.py` | 用模板写出 `README.md` / `LICENSE` / `.gitignore` |
| 5 | 本地 git | `publish.py` | `git init` + `git add -A` + 第一个 commit（已存在则跳过） |
| — | 推送前 review | `publish.py` | 打印 plan + 停下，等显式 `--yes` |
| 6 | 建仓 + 推送 | `create_repo_safe.py` | 三路径兜底：`gh CLI` → API + 钥匙串 PAT → 手把手网页教程 |
| 7 | 远端验证 | `verify_remote.py` | 确认 HEAD 一致 + 关键文件在 remote 上 |

## 硬约束（这些事它一定不做）

1. **扫到任何 RED → 拒绝继续后续 phase**（secret / 私有路径 / 敏感文件名 / 超大文件）
2. **推送必须显式 `--yes`** —— 不接受沉默确认、不接受隐含同意
3. **Token 永远不进对话上下文** —— 从系统钥匙串读 `git credential fill` → 落 0600 tempfile → 用完 shred 销毁
4. **不删除任何本地文件、不改任何代码** —— 只新写 3 个文件（README/LICENSE/.gitignore）
5. **不替你改 GitHub Settings**（visibility 切换、branch protection、Discussions、secrets 等都不管）
6. **不替你重写 git history**（`filter-branch` / `rebase -i` / `git rm` history 一律不碰）
7. **不替你判断"这个项目该不该开源"** —— 只列证据，决策权在你

## 默认决策（不主动问，全走默认）

| 决策 | 默认 | 一句话理由 |
|---|---|---|
| 仓库可见性 | **Public** | 这是"开源"工具。想先 Private 测试用 `--private`，或推完去 Settings 切 |
| License | **MIT** | 最宽松最常见，第一次开源出问题概率最小 |
| 项目类型 | 自动探测 | 决定用哪份 `.gitignore` 模板 |
| 可选 add-on（CONTRIBUTING/CHANGELOG/templates/badges） | **不加** | 真正需要时再说 |

任何决策都可以用 CLI flag 覆盖，详见 [USAGE.zh.md](USAGE.zh.md)。

## 支持的 AI 助手

skill 本质是一个目录，任何能加载 Claude 式 skill 的工具都能用：

| 助手 | 安装路径 | 怎么触发 |
|---|---|---|
| Claude Code（CLI / web / IDE） | `~/.claude/skills/github-publisher/` | `SKILL.md` description 匹配"开源 XX"这类说法 |
| Cursor / Copilot CLI（带 skill loader） | 对应的 skill 目录 | 同样的 `SKILL.md` |
| 其他读 `SKILL.md` 的 AI 工具 | 任意位置 | 指向这个目录即可 |
| **不用 AI** | 任意位置 | 直接跑 Python 脚本，详见 [USAGE.zh.md](USAGE.zh.md) |

AI 层只是 orchestrator，真正的逻辑全在 `scripts/*.py`——没 AI 也能完整发布。

## 这工具不做的事（去找别的工具）

| 你想做 | 用 |
|---|---|
| 发布到 npm / pip / cargo | 对应包注册中心的 release 流程 |
| 配 CI / GitHub Actions | 自己写 `.github/workflows/*.yml` |
| 写发布推文 / 博客 | 找写作类工具 |
| 改可见性 / 开 Discussions / 加 branch protection | 自己去 GitHub Settings 改（这风险你得自己担） |
| 重写 git history 抹掉已泄漏的 secret | [`git-filter-repo`](https://github.com/newren/git-filter-repo) 或 [BFG](https://rtyley.github.io/bfg-repo-cleaner/) |
| 把 README 翻译成别的语言 | 手工，或翻译工具 |
| 在 Linux 上测试 | 未验证，欢迎提 PR |

## 平台支持

在 **macOS** 和 **Windows** 上跑过。Linux 大概率能跑（全是 Python stdlib + 标准 git/gh 命令），但没验证。

所有脚本只用 Python `pathlib` / `subprocess` / `urllib` / `tempfile` / `shutil`——不依赖 bash 特性，不装任何第三方包。

## 文档清单

| 文档 | 内容 |
|---|---|
| [README.md](README.md) | 英文版主页 |
| [README.zh.md](README.zh.md) | 当前页（中文） |
| [INSTALL.md](INSTALL.md) · [INSTALL.zh.md](INSTALL.zh.md) | 按 OS、按 AI 客户端的安装步骤 + 鉴权配置 |
| [USAGE.md](USAGE.md) · [USAGE.zh.md](USAGE.zh.md) | 每个参数、每个 exit code、每个 phase 的详解 |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) · [TROUBLESHOOTING.zh.md](TROUBLESHOOTING.zh.md) | 常见报错 + 修法 |
| [SECURITY.md](SECURITY.md) · [SECURITY.zh.md](SECURITY.zh.md) | 安全模型、保护什么、不保护什么 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 开发环境、代码风格、怎么加模板 |
| [CHANGELOG.md](CHANGELOG.md) | 版本历史 |
| `SKILL.md` | skill 工作手册，给 AI 助手看的 |
| `references/` | 模式文档、license/gitignore/README 模板、修法 recipes |

## License

MIT —— 见 [LICENSE](LICENSE)。

作者：[@xiaomoBoy](https://github.com/xiaomoBoy)。
