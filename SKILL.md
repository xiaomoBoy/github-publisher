---
name: github-publisher
description: Use when the user wants to publish a local project (any language) to GitHub for the first time, or open-source an existing local folder. Walks through 6 phases — project detection, key decisions, security + attribution scan, file generation (README/LICENSE/.gitignore), local git, and GitHub repo creation + push. Newbie-friendly with explicit defaults and three fallback auth paths. Refuses to push when secrets are detected. Triggers on requests like "把项目开源到 GitHub"、"推到 GitHub"、"publish to GitHub"、"create a public repo"、"open source this project"、"我想发布一个开源项目"、"第一次开源不知道怎么操作".
---

# GitHub Publisher

这个 skill 只负责一件事：**帮一个本地项目（任何语言、任何类型）安全开源到 GitHub**。

目标用户是第一次 / 不太熟悉 git / GitHub / 开源流程的小白和半小白。

## Working Scope

适用场景：

- 用户说「想把这个项目开源到 GitHub」
- 用户说「第一次开源不知道怎么操作」
- 用户已有本地代码 / 脚本 / 文档项目，想推到 GitHub
- 用户说「帮我建个 GitHub 仓库把这个推上去」

不适用场景：

- 用户想发布到 npm / pip / cargo 等包注册中心（这是 release 流程，不在范围内）
- 用户想配 CI/CD / GitHub Actions（独立任务）
- 用户想做 launch 推广 / 写发布推文（找写作类 skill）
- 用户想改代码风格 / 重写代码（不是发布问题）
- 用户想做跨平台兼容性测试（不是发布问题）
- 用户的项目已经在 GitHub 了想做日常维护（这 skill 只管首次开源）

## Hard Constraints

下面 7 条是硬约束，**任何情况下都不能违反**：

1. **Phase 2 三层扫描有任何红警 → 拒绝继续 Phase 3 之后**。列出位置 + 给具体修法，等用户处理完重新跑 Phase 2 通过才放行
2. **push 必须用户显式 y 确认**，不接受隐式 yes、不接受沉默
3. **Token 永远走文件不进 conversation context**（keychain → tempfile → urllib，全程不出文件）
4. **不删除任何本地文件、不改任何代码内容**（只生成新文件、只读旧文件）
5. **不替用户改 GitHub settings**（包括 visibility 切换、Discussions、branch protection、secrets 等）
6. **不替用户做 git history 重写**（filter-branch / rebase -i / git rm 等都不要碰）
7. **不替用户判断「这个项目该不该开源」**（你只列证据，决策权在用户）

## Decision Defaults

4 个关键决策，**默认值都在表里**。用户不主动说就走默认，不要每次都问。

| 决策 | 默认 | 一句话理由 |
|---|---|---|
| 仓库可见性 | **Public** | 这是"开源"工具；想先 Private 测试可后续在 Settings 切 |
| License | **MIT** | 最宽松、最常见、第一次开源出问题概率最小 |
| 项目类型 | 自动探测 | 看 manifest 文件，影响 .gitignore 模板 |
| 文档套件 | 仅基础三件套（README/LICENSE/.gitignore） | 高级文档（CONTRIBUTING/CHANGELOG/templates/双语）默认不做，问要不要 |

## Quick Mode（默认走这个）

用户说**"开源 XX"** / **"把这个项目推到 GitHub"** / **"publish to GitHub"** → 直接走 Quick Mode，不要拆 Phase 问用户。

### 步骤

1. **Preflight**（环境自检 + AI 自动安装缺失项）

   ```bash
   python3 scripts/preflight.py
   ```

   读输出。任何 `[X]` / `[!!]` 的 **required** 项（git / git.user.name / git.user.email / network.github），按对应 `fix.current_os_cmd` 提示用户**是否要 AI 帮装**：

   ```
   缺 git。要我跑 `brew install git` 装一下吗？(y/n)
   ```

   用户 y → Bash 直接装。装完重跑 preflight 直到 `Ready`。**warning 项（gh / gh.auth / git.credential）不必强求**，只要至少一条 auth path 可用即可（preflight 末行会显示 `Available auth paths: ...`）。

2. **跑 publish.py（不带 `--yes`）**

   ```bash
   python3 scripts/publish.py <项目路径>
   ```

   默认值：
   - `--name`：项目目录名（kebab-case 化）
   - `--license MIT`
   - `--public`
   - `--description ""`（如果用户开头随口说了一句简介，把它当 `--description`）
   - `--author`：从 `gh api user` 或 `git config user.email` noreply 域名自动推断

   publish.py 会跑完 Phase 1-6（preflight → detect → scan → generate → git init+commit → 打印 plan summary），然后**以 exit 12 退出**等用户确认推送。

3. **处理硬节点**（按 exit code 路由）

   | exit | 含义 | 你该做什么 |
   |---|---|---|
   | 10 | preflight 缺关键项 | 按上面第 1 步装好再重跑 |
   | 11 | scan 红警（有 secret / 私有路径 / 大文件） | 把红警逐条展示给用户，给出修法（脚本输出已含 `fix:` 指针），**不要自己改用户代码**，等用户改完重跑 |
   | 12 | 准备好推送，等确认 | 把 plan summary 完整转给用户，问"是否推送？(y/n)"。用户明确 y → 加 `--yes` 重跑 publish.py |
   | 13 | 没有可用 auth，需手动 | publish.py 已打印手把手教程，转给用户照做即可 |
   | 0 | 全完成 | 把最终 URL 和 checklist 转给用户 |
   | 1 | 其他错误 | 看 log 找原因 |

4. **不要自己跳过 exit 12 的确认**。Hard Constraint #2 仍生效：push 必须用户显式 y。

### 用户主动要"自定义"才进 Step-by-step Mode

只在用户明确说要换 license / 改 description / 选 add-on / 想分步看 / Quick Mode 失败需要排错时，才走下面的 Phase 0-6 详细流程。否则按默认值走完最省事。

---

## Step-by-step Mode（细节流程 / 备选 / 排错）

### Phase 0 — 项目识别

**做什么**：让 skill 看清楚用户要发的是什么。

```bash
python3 scripts/detect_project_type.py <项目路径>
```

输出：

- 项目根目录
- 文件总数 / 总大小
- 推测的项目类型（Python / Node / Shell / Docs / Mixed / Unknown）
- 是否已经是 git 仓库（git init 过）
- 是否检测到 fork 信号（git remote 有 upstream / package.json forkOf）

把这份报告**一句话**告诉用户，确认是不是要发这个项目。

### Phase 1 — 4 个决策

**一次问完**，每个有默认值 + 一句话理由（见上面 Decision Defaults）。

可选 add-on（默认都不加，问用户要不要）：

- 加 CONTRIBUTING.md
- 加 CHANGELOG.md
- 加 .github/ISSUE_TEMPLATE + PR_TEMPLATE
- 加 README badges
- 加中文 README（双语）
- **加 Claude Code marketplace 元数据**（只在项目里有 SKILL.md 文件时才问）

### Phase 2 — 三层扫描（核心，0 红警才能进下一 Phase）

```bash
python3 scripts/scan_project.py <项目路径>
```

扫三层：

**① 私有数据**
- 个人路径硬编码（`/Users/<name>` / `/home/<name>` / `C:\Users\<name>` / `~/`）
- Secret patterns（`sk-...` / `ghp_...` / `AKIA...` / PEM private-key headers / 等，完整清单见 `references/private-data-patterns.md`）
- 敏感文件名（`.env` / `*.key` / `id_rsa*` / `credentials.json` / `*.pem` / `*.pfx`）

**② Attribution / 版权**
- Fork 信号：`git remote -v` 含 upstream / `.git/config` 含 fork from / manifest 标识
- 第三方代码目录：`vendor/` / `third_party/` / `external/` / 含 `LICENSE` 文件的子目录
- 注释关键词（标识第三方代码的常见短语，完整清单见 `references/attribution-patterns.md`）

**③ 大文件**
- 单文件 > 50 MB（GitHub 上限 100 MB，提前预警）

任何红警 → 列具体位置 + 走 `references/secret-fix-recipes.md` 给修法。**不让进 Phase 3**。

### Phase 3 — 生成必备 + 自动加 attribution 段落

```bash
python3 scripts/generate_files.py <项目路径> --license MIT --type python
```

生成 3 个必备文件：

- `.gitignore`（按 Phase 0 探测的项目类型，从 `references/gitignore-templates/` 选）
- `LICENSE`（按 Phase 1 决策，从 `references/license-templates/` 选）
- `README.md`（从 `references/readme-templates/basic.md` 起手）

README 模板**根据 Phase 2 扫描结果自动加段落**：

- 如果是 fork → 顶部加 `> This is a fork of [upstream URL]. Original work by [author].`
- 如果检测到第三方代码 → 末尾加 `## Acknowledgements` 列出每个发现项 + 提示用户补全归属
- **末尾默认加 `## Platform Compatibility`**：根据探测的当前 OS 写默认值（`Tested on macOS / Windows. Other platforms may work but are not verified.`）

Phase 1 选了的可选 add-on 一并生成。

### Phase 4 — 本地 git 准备

```bash
python3 scripts/check_git_config.py <项目路径>
```

做这些事：

1. 没有 git 仓库 → `git init -b main`
2. 检测 `git config user.email` 是否疑似私人邮箱（不是 `*@users.noreply.github.com`、不是工作域名）
   - 是 → **软提示**："你 commit 用的邮箱是 `<X>`，会全网可见。想隐私可以改成 `<your-username>@users.noreply.github.com`，命令: `git config user.email '...'`。要改吗？(y/n/skip)"
   - 不强制，用户说 skip 就 skip
3. 列出 staged 文件给用户 review
4. 用户显式确认后 commit（默认 message `Initial commit`，可改）

### Phase 5 — GitHub 建仓 + push（三路径兜底）

```bash
python3 scripts/create_repo_safe.py <repo-name> --public
```

按以下顺序尝试：

**路径 A — gh CLI 可用** → `gh repo create <name> --public --source=. --remote=origin --push`

**路径 B — gh 不可用但 keychain 有 PAT** → API 直建（`urllib.request` POST `/user/repos`，token 从 `git credential fill` 读到 tempfile，全程不进 conversation context），然后 `git push -u origin main`

**路径 C — 都没有** → 走 `references/github-no-gh-walkthrough.md` 手把手教用户在网页建仓 + 给 `git remote add origin ... && git push -u origin main` 命令让用户自己跑

**所有路径在 push 前都必须**：

- 一句话风险提示："push 后这些文件就在公网上了。一旦推上去，即使删仓库也可能被爬虫缓存。确认 Phase 2 扫描全过了吗？(y/n)"
- 等用户显式 y 才执行

### Phase 6 — 远端验证 + 完成 checklist

```bash
python3 scripts/verify_remote.py <repo-url>
```

验证：

- 远端文件数 = 本地 commit 文件数？
- 关键文件（README / LICENSE / .gitignore）都在远端？
- 输出仓库 URL，可选用 `python3 -c "import webbrowser; webbrowser.open('<url>')"` 浏览器打开

**最终输出三段 checklist**：

```
✅ 已完成：
   • 创建 GitHub 仓库 <url>（Public / MIT）
   • 推送 N 个文件
   • 添加 README / LICENSE / .gitignore
   • 安全扫描全过（私有数据 / attribution / 大文件 0 红警）
   • [如有] 加入 fork attribution / Acknowledgements 段落
   • Platform 声明 (Tested on <OS>, others not verified)

⚪ 可选 (要不要做我可以接着帮你)：
   • 在 GitHub Settings 加 description 和 topics（建议: <skill 根据项目自动给 5 个>）
   • 开启 Discussions (Settings → Features)
   • 打 v0.1.0 tag + 写 release notes
   • 生成 CONTRIBUTING.md / CHANGELOG.md
   • 添加 README badges
   • 加中文 README
   • [若 Phase 1 没选] 加 Claude Code marketplace 元数据

⛔ 不在我范围内 (要做请另找工具)：
   • 发推广 / 写 launch 推文
   • 配 CI/CD (GitHub Actions)
   • 发到 npm / pip / cargo 等包注册中心
   • 改代码风格 / 重写代码
   • 跨平台兼容性测试（Linux 等）
```

## Optional Add-ons

详见 [references/optional-add-ons.md](references/optional-add-ons.md)。Phase 1 没选的，Phase 6 后用户可以随时让你回来加。

## Platform Support

本 skill 自身在 **macOS 和 Windows** 上工作。所有脚本用 Python stdlib（pathlib + subprocess + urllib + tempfile + webbrowser），无 shell-specific 假设。

Linux 大概率能跑但未验证。报问题去仓库 issue。

**生成的项目** README 会自动加 Platform 声明：默认写「Tested on <当前 OS>」，明确"其他平台未验证"，让用户后续若添加更多平台支持时手动更新。

## Troubleshooting

常见报错 + 修法见 [references/troubleshooting.md](references/troubleshooting.md)。覆盖：

- `Permission denied (publickey)` —— SSH key 没配
- `Authentication failed` —— PAT 过期 / 无权限
- gh 命令找不到
- push 报远端有冲突
- secret 扫到不知道怎么改

## References / Scripts

- `references/private-data-patterns.md` —— 私有数据扫描 patterns 清单
- `references/attribution-patterns.md` —— Fork / 第三方代码 / 注释检测规则
- `references/license-chooser-newbie.md` —— License 一句话理由
- `references/secret-fix-recipes.md` —— 常见 secret 怎么改
- `references/github-no-gh-walkthrough.md` —— 没 gh 时的网页 + 命令手把手
- `references/troubleshooting.md` —— 常见报错
- `references/optional-add-ons.md` —— Phase 6 可选项怎么做
- `references/license-templates/{MIT,Apache-2.0,GPL-3.0}.txt`
- `references/gitignore-templates/{python,node,shell,docs,general}.gitignore`
- `references/readme-templates/{basic,with-fork-attribution,with-acknowledgements}.md`
- `scripts/preflight.py` —— Quick Mode 第 1 步：环境自检 + 给 AI 看的安装命令
- `scripts/publish.py` —— Quick Mode 第 2 步：一键 orchestrator（按 exit code 路由）
- `scripts/detect_project_type.py` —— Phase 0
- `scripts/scan_project.py` —— Phase 2（核心）
- `scripts/generate_files.py` —— Phase 3
- `scripts/check_git_config.py` —— Phase 4
- `scripts/create_repo_safe.py` —— Phase 5
- `scripts/verify_remote.py` —— Phase 6
