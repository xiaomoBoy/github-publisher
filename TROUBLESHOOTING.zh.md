# 故障排查

English → [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

按错误信息搜（Ctrl/Cmd-F）。每条结构：**含义** → **修法**。

- [安装 / 环境](#安装--环境)
- [鉴权（gh / PAT / SSH）](#鉴权gh--pat--ssh)
- [推送错误](#推送错误)
- [扫描错误 / 误报](#扫描错误--误报)
- [网络 / 代理](#网络--代理)
- [AI 助手不触发 skill](#ai-助手不触发-skill)
- [工具 / phase 相关](#工具--phase-相关)
- [重置 / 恢复](#重置--恢复)

---

## 安装 / 环境

### `git: command not found` / `'git' is not recognized`

**含义**：git 没装或不在 `PATH`。

**修法**：

```bash
# macOS
brew install git

# Windows PowerShell
winget install --id Git.Git
# 然后新开一个 PowerShell 窗口
```

### `python3: command not found`（Windows）

Windows 安装器有时只注册 `python` 不注册 `python3`。试 `python --version`。能跑就把文档里所有 `python3` 替换成 `python`。

或者去 <https://python.org/downloads> 安装时勾上 **"Add Python to PATH"**。

### 跑 `python3` 显示 `Python 2.x`

老系统把 `python3` 别名指向了 Python 2。检查：

```bash
python3 -V
```

显示 2.x 就装一个新的 Python 3（macOS `brew install python@3.11`，Windows 用安装器）。

### preflight 显示 `[X ] git.user.name` / `[X ] git.user.email`

没设过 git 身份。全局设上（所有仓库共用）：

```bash
git config --global user.name "你的名字"
git config --global user.email "you@example.com"
```

想保留真实邮箱隐私用 GitHub noreply 别名——见 [INSTALL.zh.md § 邮箱隐私](INSTALL.zh.md#邮箱隐私)。

---

## 鉴权（gh / PAT / SSH）

### `gh: command not found`

**含义**：`gh` CLI 没装。这是可选的——工具会回退到 Path B（PAT）或 Path C（手动）。

**修法**（想用 Path A）：

```bash
# macOS
brew install gh

# Windows
winget install --id GitHub.cli
```

装完：`gh auth login`。

### `gh auth status` 显示 "You are not logged into any GitHub hosts"

```bash
gh auth login
```

选：`GitHub.com` → `HTTPS` → `Yes (authenticate Git)` → `Login with a web browser`。

### `Authentication failed for 'https://github.com/...'`

**含义**：HTTPS push 用了密码但 GitHub 不再接受密码。要用 Personal Access Token（PAT）。

**修法**：

1. 生成：<https://github.com/settings/tokens/new>
2. Scopes：勾 `repo`
3. 点 **Generate token** —— **立刻复制**（关掉就再也看不到了）
4. 重跑 `git push`。问 username 填 GitHub 登录名，问 password **粘贴 PAT**。
5. 想让下次自动记住，设凭据助手：

   ```bash
   # macOS
   git config --global credential.helper osxkeychain
   # Windows
   git config --global credential.helper manager
   ```

### `git push` 报 `Permission denied (publickey)`

**含义**：用了 SSH remote URL 但 GitHub 不认识你的 SSH key。

**最快修法**：换成 HTTPS：

```bash
git remote set-url origin https://github.com/<你的用户名>/<repo>.git
git push -u origin main
```

会问 username + password（password 用 PAT）。

**正经修法**：生成 SSH key 并加到 GitHub：

```bash
ssh-keygen -t ed25519 -C "you@example.com"
# 一路回车，密码可空

# macOS / Linux
cat ~/.ssh/id_ed25519.pub

# Windows PowerShell
Get-Content $env:USERPROFILE\.ssh\id_ed25519.pub
```

复制输出，去 <https://github.com/settings/keys> → **New SSH key** 粘贴。

### preflight 显示 `git.credential` 是 `warning: No PAT cached`

只是说 Path B 当前不能用。如果 Path A（`gh`）OK，不用管。想专门用 Path B：

1. 生成 PAT（见上）
2. 设凭据助手（见上）
3. 跑一次 `git fetch` / `git push` 私有仓库——git 会提示并缓存 PAT

---

## 推送错误

### `Updates were rejected because the remote contains work that you do not have locally`

**含义**：GitHub 上仓库有你本地没有的 commit。多半因为创仓库时勾了 "Add README"。

**修法**：

```bash
git pull origin main --rebase
git push -u origin main
```

冲突一堆，最干净是**删了 GitHub 上的仓重新建**（确保任何 checkbox 都不勾）。

### `fatal: remote origin already exists`

**含义**：之前已经配过 `origin`。`publish.py` Phase 6 有安全检查，如果 `origin` 指别处会 exit 4——见下节。

如果只是想手动换：

```bash
git remote set-url origin <新-url>
```

### `publish.py` / `create_repo_safe.py` exit 4

含义：`origin` 已配置但指向**不是**我们要推的 URL。工具拒绝静默覆盖。打印的 hint 给三个选项：

1. **已经指对了？** 自己 `git push -u origin main`。
2. **想替换？** `python3 scripts/create_repo_safe.py … --force-overwrite-origin`
3. **想从头开始？** `git remote remove origin`，再跑 `publish.py`

### `remote: error: File X is XX MB; this exceeds GitHub's file size limit`

**含义**：commit 里有 > 100 MB 的文件，GitHub 拒收。

**修法**：

```bash
# 1. 加进 .gitignore
echo "<path>" >> .gitignore

# 2. 取消追踪
git rm --cached <path>
git commit -m "Stop tracking large file"
git push -u origin main
```

如果大文件已经 commit 过（不只在 staged），要重写 history：

```bash
pip install git-filter-repo
git filter-repo --invert-paths --path <path>
git push --force-with-lease
```

`--force-with-lease`（不是 `--force`）更安全——不会覆盖你没看过的远端工作。

真要追踪大文件用 [Git LFS](https://git-lfs.github.com/)。

---

## 扫描错误 / 误报

### Scan 把我文档里的示例字符串标成 secret

那个文件就是为了文档化模式或修法存在的——故意有看起来像 secret 的东西。

**修法**：在文件前 2 KB 内加 `scan-ignore-file` marker：

```
<!-- scan-ignore-file: 这是一份故意列出示例模式的参考文档 -->
```

或 Python：

```python
# scan-ignore-file: 模式源码自命中
```

什么场合适合用、什么场合不适合，见 [USAGE.zh.md § scan-ignore-file 标记](USAGE.zh.md#scan-ignore-file-标记)。

### Scan 标到一个我不小心 commit 的真 secret

修法分两步：

1. **止血**：按 [`references/secret-fix-recipes.md`](references/secret-fix-recipes.md) 从工作树移除 secret。重跑 scan 确认 GREEN。

2. **撤销 secret**：哪怕下个 commit 删了，泄漏的值**已经在 git history**（以及别人的 clone 里）。必须去对应服务（OpenAI / GitHub / AWS 等）**撤销泄漏的 token，生成新的**。

本工具不重写 git history——见 [SECURITY.zh.md](SECURITY.zh.md)。要重写用 [`git-filter-repo`](https://github.com/newren/git-filter-repo) 或 [BFG](https://rtyley.github.io/bfg-repo-cleaner/)，但要明白：已经 push 过的 history 可能在 GitHub 缓存 / fork 里留存，重写也未必能彻底清除。

### Scan 改了之后还在标同样的东西

三种可能：

1. **改了没存**就重跑了。存盘再跑。
2. **secret 在另一个文件**里有类似内容。仔细看 scan 输出里的 `file:line`。
3. **secret 在 git history 里**，但 scan 只看工作树。当前工作树修好足以止血，但历史泄漏仍在——按上一题处理。

### Scan 报了 `attribution_comments` 但我没第三方代码

scanner 拿到了一条代码注释，里面恰好有 "based on" / "inspired by" / "@author"？只扫代码扩展名（`.py`、`.js`、`.rs` 等），所以你代码里有匹配。要么：

- 改一下注释措辞（如果实际不是引用归属）
- 给文件加 `scan-ignore-file` marker（仅在这个文件是参考/模板文档时）

---

## 网络 / 代理

### `Could not resolve host: github.com`

**含义**：DNS 或网络问题。

**诊断**：

```bash
ping github.com
curl -v https://github.com
```

用代理：

```bash
git config --global http.proxy http://127.0.0.1:7890
git config --global https.proxy http://127.0.0.1:7890
```

（`7890` 换成你代理端口）

不用代理后记得取消：

```bash
git config --global --unset http.proxy
git config --global --unset https.proxy
```

### preflight 显示 `network.github` 是 `cannot reach api.github.com`

同上。工具需要访问 `api.github.com` 建仓 + `github.com` 推送，两个都得通。

GitHub 访问不稳定的地区考虑用 VPN 或代理。

### `SSL: CERTIFICATE_VERIFY_FAILED`

**含义**：Python 的 CA bundle 坏了。

**macOS 修法**（Python.org 安装后）：

```bash
/Applications/Python\ 3.11/Install\ Certificates.command
```

或：

```bash
pip install --upgrade certifi
```

---

## AI 助手不触发 skill

### "我说了'开源 XX'但 AI 没跑 skill"

**检查**：

1. skill 目录在 `~/.claude/skills/github-publisher/`（或你客户端期望的路径）
2. 目录里根有 `SKILL.md`
3. 装完后**重启了** AI 客户端
4. 触发说法能被识别——试这些：
   - "open source `/path/to/project`"
   - "publish this folder to GitHub"
   - "把这个项目推到 GitHub"
   - "create a public GitHub repo from `<path>`"

Claude Code：skill 在 session 启动时加载。重启 CLI / IDE 扩展。

### "AI 开始干了但跑了错的命令"

如果看到 AI 自己拼 `git` 命令而不是调 `python3 scripts/publish.py`，说明 skill 没加载。验证目录：

```bash
ls ~/.claude/skills/github-publisher/
# 应该看到：LICENSE  README.md  SKILL.md  references/  scripts/  ...
```

### "AI 跑了 preflight 但忽略了输出"

打开 SKILL.md 检查是否被截断（YAML frontmatter 被破坏）。`name:` 和 `description:` 行必须完整，文件必须以 `---` 开头。

---

## 工具 / phase 相关

### `exit 10` —— preflight 不 ready

必需工具缺失或没配置。exit 之前的 preflight 输出告诉你具体是哪个和怎么修。最常见：git 没装，或 `git config user.email` 没设。

### `exit 11` —— scan RED

检测到（疑似）secret / 私有路径 / 敏感文件。scan 输出列每个 finding 的位置和修法。按 [`references/secret-fix-recipes.md`](references/secret-fix-recipes.md) 修了重跑。

### `exit 12` —— pre-push review

**不是错误。** 这是 push 前的显式 checkpoint。看打印的 plan，没问题加 `--yes` 重跑同一条命令。

### `exit 13` —— 走到 Path C（手动）

`gh` 和缓存 PAT 都没有。按打印的 walkthrough 做——浏览器几步 + 一条终端命令。或者装 `gh` / 配 PAT 后重跑（见 [INSTALL.zh.md § Step 4](INSTALL.zh.md#step-4--配置-github-鉴权)）。

### `publish.py` 卡在 Phase 6

`git push` 可能在等凭据输入。开另一个终端手动跑同样的 `git push -u origin main`——如果它要凭据，喂进去并让 git 缓存（再重跑 `publish.py`）。

### Phase 4 全显示 `[skip]`

三个文件（`README.md` / `LICENSE` / `.gitignore`）已经存在，工具默认 skip（避免覆盖手动改过的内容）。想重生成（如改了 `--description`）：

```bash
python3 scripts/publish.py /path/to/folder --description "..." --regenerate-docs
```

---

## 重置 / 恢复

### "想撤销 publish.py 在本地干的所有事"

```bash
cd /path/to/folder
rm -rf .git LICENSE README.md .gitignore
```

回到 Phase 4-5 之前的状态。（源代码从未被碰过。）

### "想删 GitHub 上刚建的仓库"

工具故意不替你删——这是对远端系统的破坏性操作。

```bash
# gh CLI（会让你打仓库名确认）
gh repo delete <owner>/<repo>

# 或网页：Settings → General → Danger Zone → Delete this repository
```

### "不小心 push 了 secret"

1. 立刻去对应服务（OpenAI / GitHub / AWS 等）**撤销泄漏的 token**。这一步最重要。
2. 生成新 token 更新本地配置。
3. 可选：用 `git-filter-repo` 或 BFG 重写 history，然后 `git push --force-with-lease`。**但要明白**：GitHub 可能缓存泄漏的 commit，force-push 之前 clone 过的人还持有旧 history。
4. 真正的修复永远是第 1 步。不要因为"history 改了"就跳过它。

详见 [`references/secret-fix-recipes.md § git history`](references/secret-fix-recipes.md)。

---

问题不在这？开 issue：<https://github.com/xiaomoBoy/github-publisher/issues>。请附：
- 你跑的确切命令
- 完整输出（涉及 secret 的部分先打码）
- OS + `python3 --version`
- preflight 有没有通过
