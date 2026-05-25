# 安装指南

English → [INSTALL.md](INSTALL.md)

本文档包含：
- [前置条件](#前置条件)
- [Step 1 — macOS 安装](#step-1--macos-安装)
- [Step 1 — Windows 安装](#step-1--windows-安装)
- [Step 2 — 放置 skill](#step-2--放置-skill)
- [Step 3 — 用 preflight 验证](#step-3--用-preflight-验证)
- [Step 4 — 配置 GitHub 鉴权](#step-4--配置-github-鉴权)
- [按 AI 客户端配置](#按-ai-客户端配置)
- [不用 AI 独立运行](#不用-ai-独立运行)
- [卸载](#卸载)

---

## 前置条件

必需：

- **Python 3.8+**（推荐 3.10+），只用标准库，无需 `pip install`
- **git** 2.x 或更新
- 一个 **GitHub 账号**（免费版即可）
- 能访问 `api.github.com` 和 `github.com`

可选（用上更顺，但不强求）：

- **`gh` CLI** —— 启用最自动化的鉴权路径（Path A）。没 `gh` 也能用，工具会回退到 `git credential`（Path B）或手动网页流程（Path C）。

哪怕 `gh` 和 `git credential` 都没有也行——Path C 只是把每条该跑的命令明明白白打出来给你照着做。

---

## Step 1 — macOS 安装

```bash
# 已经装过的可以跳过对应行
brew install git python@3.11
brew install gh             # 可选，但推荐
```

验证：

```bash
git --version       # git version 2.x
python3 --version   # Python 3.x
gh --version        # gh version 2.x   （可选）
```

`brew` 都没有？去 <https://brew.sh> 装一下。

---

## Step 1 — Windows 安装

用 **PowerShell**（别用 `cmd.exe`）。

```powershell
# 已经装过的可以跳过对应行
winget install --id Git.Git
winget install --id Python.Python.3.11
winget install --id GitHub.cli       # 可选，但推荐
```

安装完**新开一个 PowerShell 窗口**让 `PATH` 生效。

验证：

```powershell
git --version
python --version       # 也可能是 python3，看安装方式
gh --version           # 可选
```

如果只有 `python3` 没有 `python`，把文档里所有 `python` 替换成 `python3`。

> 提示：喜欢类 unix 风格命令的话用 Git Bash（Git for Windows 自带）。文档里的命令在 PowerShell 和 Git Bash 都能跑。

---

## Step 2 — 放置 skill

skill 就是一个目录。放哪里取决于你怎么用它。

### 用 Claude Code

```bash
# macOS / Linux / Git Bash
git clone https://github.com/xiaomoBoy/github-publisher.git ~/.claude/skills/github-publisher
```

```powershell
# Windows PowerShell
git clone https://github.com/xiaomoBoy/github-publisher.git $env:USERPROFILE\.claude\skills\github-publisher
```

下次启动 Claude Code 时会自动从 `~/.claude/skills/` 加载。

### 用别的支持 skill 的 AI 工具

按那个工具的 skill 加载路径放就行。skill 本质就是一个含 `SKILL.md` 的文件夹。

### 不用 AI 独立运行

clone 到任意位置，直接跑脚本：

```bash
git clone https://github.com/xiaomoBoy/github-publisher.git
cd github-publisher
python3 scripts/preflight.py
```

---

## Step 3 — 用 preflight 验证

`preflight.py` 检查每一项前置条件，缺啥就告诉你**确切的安装命令**（按你的 OS 给）：

```bash
python3 ~/.claude/skills/github-publisher/scripts/preflight.py
```

全过会长这样：

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

如果出现 `[X ]`（必需项缺失）或 `[!!]`（必需项需配置），preflight 会直接打印修法命令。**不需要记任何东西——按提示复制粘贴跑命令，重跑 preflight 直到全绿。**

标了 `[~ ]  (optional)` 的不阻塞发布，只是少一条更顺的路径。

### 常见 preflight 结果

| 现象 | 含义 | 修法 |
|---|---|---|
| `[X ] git` | git 没装 | 按提示跑 `brew install git` / `winget install --id Git.Git` |
| `[!!] git.user.name` | 没设过名字 | `git config --global user.name "你的名字"` |
| `[!!] git.user.email` | 没设过邮箱 | `git config --global user.email "you@example.com"`（或用 noreply，见下面） |
| `[X ] network.github` | 连不上 `api.github.com` | 查 VPN / 代理 / 防火墙 |

---

## Step 4 — 配置 GitHub 鉴权

工具按顺序尝试 3 条鉴权路径，**只要任意一条能用就行**。

### Path A — `gh` CLI（推荐，最自动化）

```bash
gh auth login
```

选：
- `GitHub.com`
- `HTTPS`
- `Yes`（让 Git 用 GitHub 凭据认证）
- `Login with a web browser`

浏览器走完流程就登录好了。验证：

```bash
gh auth status
```

### Path B — `git credential`（PAT 存系统钥匙串）

不想用 `gh` 也行，可以让 git 把 PAT 缓存在系统钥匙串里。工具通过 `git credential fill` 读 token —— **全程不进 plain text**。

1. 生成 PAT：<https://github.com/settings/tokens/new>
2. 设置：
   - **Note**：任意名字（如"我的电脑"）
   - **Expiration**：`90 days` 或 `No expiration`
   - **Scopes**：勾 `repo` 一个就够
3. 点 **Generate token**，**立刻复制**（关掉就再也看不到了）
4. 设凭据助手让 git 记住：
   - macOS: `git config --global credential.helper osxkeychain`
   - Windows: `git config --global credential.helper manager`
5. 第一次 `git push` 时 git 会问用户名 + 密码。用户名填 GitHub 登录名，**密码粘贴刚生成的 PAT**。然后就缓存进钥匙串。

之后 `git credential fill` 会静默返回缓存的 PAT，工具走 Path B。

### Path C — 手动网页流程（不用鉴权）

A 和 B 都不行，`publish.py` 会自动 fall back 到 Path C：打出一份精确的命令清单 + 网页操作步骤，你按着做。需要：

1. 打开 <https://github.com/new>
2. 填仓库名（walkthrough 里有，照填）
3. **不要**勾 Add README / .gitignore / license 三个 checkbox（本地已经生成了）
4. 点 **Create repository**
5. 跑 walkthrough 打出来的 `git remote add origin ... && git push -u origin main`

只要你有 GitHub 账号 + 浏览器，Path C 永远能用。

### 邮箱隐私

默认 `git commit` 记的是 `git config user.email` 那个邮箱，**仓库 URL 一公开，每个 commit 的邮箱所有人都看得到**。

想保留真实邮箱隐私，用 GitHub 的 noreply 别名：

1. 去 <https://github.com/settings/emails> 找你的别名，格式 `<id>+<username>@users.noreply.github.com`（老账号是 `<username>@users.noreply.github.com`）。
2. 设上：

   ```bash
   git config --global user.email "<你的用户名>@users.noreply.github.com"
   ```

`preflight.py` 和 `check_git_config.py` 检测到你配的邮箱像私人邮箱（gmail / outlook / qq 等）时会软提示——只警告不改，由你自己决定。

---

## 按 AI 客户端配置

### Claude Code（CLI / web / IDE）

`git clone` 到 `~/.claude/skills/github-publisher/` 之后重启 Claude Code，skill 自动发现。

触发说法：

- "开源 `/path/to/my-project`"
- "把这个项目推到 GitHub"
- "publish this folder"

Claude 读 `SKILL.md`，走 Quick Mode（preflight → publish.py），只问你 1-2 个 y/n（装缺的工具？推送？）。

### Cursor / 其他 AI 编辑器

如果支持从目录加载 skill，把路径指向 `~/.claude/skills/github-publisher/` 即可。触发说法一样。

### Copilot CLI / Gemini CLI

如果支持 `SKILL.md` 式 skill，放到它期望的路径即可。否则当作独立工具用（下一节）。

### "我就想跑脚本"

整个工具就是 `scripts/*.py`，不需要任何 AI，见下一节。

---

## 不用 AI 独立运行

直接驱动 `publish.py` 即可。推荐流程：

```bash
# 快速体检（信息性质，全过 exit 0）
python3 scripts/preflight.py

# Dry run：跑完 Phase 5 后停下，打印 plan，exit 12
python3 scripts/publish.py /path/to/my-project \
    --name my-tool \
    --description "一句话简介" \
    --license MIT \
    --public

# 看完打印的 plan 再决定推送：
python3 scripts/publish.py /path/to/my-project \
    --name my-tool \
    --description "一句话简介" \
    --license MIT \
    --public \
    --yes
```

`--yes` 是显式的推送确认，不带它 `publish.py` 永远不推（硬约束 #2）。

完整参数列表见 [USAGE.zh.md](USAGE.zh.md)。

---

## 卸载

```bash
# macOS / Linux
rm -rf ~/.claude/skills/github-publisher

# Windows PowerShell
Remove-Item -Recurse -Force $env:USERPROFILE\.claude\skills\github-publisher
```

完了。这个工具不写自己目录和目标项目以外的任何文件，不往全局 Python 装东西。

如果之前为这个工具专门配的凭据助手或生成的 PAT，可以一并清理：

- <https://github.com/settings/tokens>（撤销 PAT）
- `git config --global --unset credential.helper`（移除助手）
