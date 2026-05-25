# 使用说明

English → [USAGE.md](USAGE.md)

本文档包含：
- [TL;DR](#tldr)
- [两种使用方式](#两种使用方式)
- [`publish.py` 参数手册](#publishpy-参数手册)
- [`preflight.py` 参数手册](#preflightpy-参数手册)
- [7 个 phase 详解](#7-个-phase-详解)
- [Exit code 一览](#exit-code-一览)
- [常见场景](#常见场景)
- [Fork 项目和第三方代码](#fork-项目和第三方代码)
- [`scan-ignore-file` 标记](#scan-ignore-file-标记)
- [自定义模板](#自定义模板)
- [单独跑每个脚本](#单独跑每个脚本)

---

## TL;DR

```bash
# 通过 AI 助手：
# > "开源 /path/to/my-project"

# 独立运行：
python3 scripts/publish.py /path/to/my-project           # 跑完 plan，停在 exit 12
python3 scripts/publish.py /path/to/my-project --yes     # 真正推送
```

整个流程就这些。下面都是细节。

---

## 两种使用方式

### 方式 1 —— AI 助手（Quick Mode）

你说：*"开源 /path/to/my-project"*。

AI：
1. 跑 `preflight.py`。缺啥必需项 → 问你一次 `y/n` 装不装。
2. 用默认值跑 `publish.py <path>`，停在 "Pre-push review"，退出码 12。
3. 把打印的 plan 转给你，问：*"推送 (y/n)?"*。
4. 你 `y` → AI 重跑 `publish.py <path> --yes` 推送 + 验证。

整个流程你只需要回答两个 y/n（装工具 + 确认推送）。

### 方式 2 —— 独立运行（不用 AI）

直接跑 `publish.py`，带你想要的参数。仍然会在 push 前停（exit 12），加 `--yes` 重跑才推。

两种方式跑的是同一份脚本。AI 只是省事，不是必要。

---

## `publish.py` 参数手册

```
python3 scripts/publish.py <path> [options]
```

`<path>` 是项目根目录（你想发布的文件夹）。

### 参数

| 参数 | 默认 | 作用 |
|---|---|---|
| `--name <name>` | `<path>` 的目录名（kebab-case 化） | GitHub 上的仓库名 |
| `--license <id>` | `MIT` | `MIT` / `Apache-2.0` / `GPL-3.0` 三选一 |
| `--public` | （默认） | 公开仓库 |
| `--private` | | 私有仓库 |
| `--description "<text>"` | 空 | 一句话简介，进 GitHub 仓库头和 README |
| `--author <username>` | 自动识别 | GitHub 用户名（用于 README + LICENSE）。从 `gh api user` 或 git noreply 邮箱自动推断 |
| `--type <type>` | 自动探测 | 强制指定项目类型：`python` / `node` / `shell` / `docs` / `claude-skill` / `general`。决定 `.gitignore` 模板 |
| `--commit-message "<msg>"` | `Initial commit` | 第一个 commit 的消息 |
| `--install-cmd "<cmd>"` | 占位符 | 生成 README 时的真实 install 段内容 |
| `--usage-example "<cmd>"` | 占位符 | 生成 README 时的真实 usage 段内容 |
| `--regenerate-docs` | 关 | 覆盖已存在的 `README.md` / `LICENSE` / `.gitignore`。默认 skip（保护手动改过的内容） |
| `--yes` | 关 | 显式推送确认。**不带这个旗工具永不推送** |
| `--skip-preflight` | 关 | 跳过 Phase 1 |
| `--no-push` | 关 | 只跑 Phase 1-5，不建仓不推送不验证 |
| `--format <fmt>` | `human` | `human`（人类可读 log）或 `json`（一坨 JSON 含全部 state，给 AI 用） |

### 最小示例

```bash
# 全默认
python3 scripts/publish.py /path/to/my-tool

# 自定义 name + description
python3 scripts/publish.py /path/to/my-tool \
    --name awesome-tool \
    --description "A nifty CLI for X"

# 私有仓库
python3 scripts/publish.py /path/to/my-tool --private

# Apache 2.0 协议
python3 scripts/publish.py /path/to/my-tool --license Apache-2.0

# 改了 --description 后强制重生成 README/LICENSE/.gitignore
python3 scripts/publish.py /path/to/my-tool --description "新" --regenerate-docs
```

---

## `preflight.py` 参数手册

```
python3 scripts/preflight.py [--format human|json]
```

检查项：

- `python3`（你正在跑它，所以肯定有，只报版本）
- `git`（装了吗？版本？）
- `git.user.name` / `git.user.email`（全局配置了吗？）
- `gh` CLI（装了吗？）
- `gh.auth`（登录了吗？）
- `git.credential`（钥匙串里有 PAT 缓存吗？）
- `network.github`（能连 `api.github.com` 吗？）

退出码：

- `0` — ready（至少一条 auth 路径可用）
- `1` — 缺必需工具
- `2` — ready 但只剩 manual auth 路径

必需项（缺了 preflight 会给你确切的 OS 安装命令）：

- `python3`
- `git`
- `git.user.name`
- `git.user.email`
- `network.github`

可选项（缺了照样能 publish，只是少一条更顺的路径）：

- `gh`
- `gh.auth`
- `git.credential`

---

## 7 个 phase 详解

### Phase 1 — Preflight

内部调用 `preflight.py`。任何必需项失败，`publish.py` 立即 exit 10——项目零改动。

跳过：`--skip-preflight`（适合 CI 环境，已经预先验证过）。

### Phase 2 — Detect project

调用 `detect_project_type.py`。看：

- 根目录的 manifest 文件：`package.json` → node，`pyproject.toml` → python，等
- 是否存在 `SKILL.md` → claude-skill
- 文件扩展名分布作为兜底
- 是否有 `.git/`，是否有 `upstream` remote（fork 信号）

探测出来的 type 喂给 Phase 4（决定 `.gitignore` 模板）。可以用 `--type` override。

### Phase 3 — 三层扫描

调用 `scan_project.py`。三层：

| 层 | 查什么 | RED 后果 |
|---|---|---|
| 私有数据 | 硬编码 `/Users/<name>` / `/home/<name>` / `C:\Users\<name>`；强 secret 模式（`sk-…`、`ghp_…`、`AKIA…`、PEM 私钥头等）；敏感文件名（`.env`、`id_rsa`、`*.pem` 等） | RED — 中止流程，exit 11 |
| 引用归属 | fork 信号；第三方代码目录（`vendor/`、`third_party/` 等）；代码文件中的引用注释 | 信息性 — README 自动补段落 |
| 大文件 | > 50 MB 的单文件 | YELLOW；> 100 MB 触发 RED（GitHub 硬上限） |

任何 RED 都**阻止 Phase 4 及之后**。必须按 [`references/secret-fix-recipes.md`](references/secret-fix-recipes.md) 修完再重跑。

文档里的"示例数据"被误报？用 [`scan-ignore-file` 标记](#scan-ignore-file-标记)。

### Phase 4 — Generate

调用 `generate_files.py`。写（除非已存在）：

- `LICENSE` —— 按 `--license` 挑模板，替换 `{YEAR}` 和 `{COPYRIGHT_HOLDER}`（= `--author`）
- `.gitignore` —— 按 `--type`（或 Phase 2 探测的类型）挑模板
- `README.md` —— 三选一：
  - `basic` —— scan 干干净净
  - `with-fork-attribution` —— Phase 3 检测到 fork 信号
  - `with-acknowledgements` —— Phase 3 检测到第三方目录或引用注释

三个目标文件中已存在的，**默认 skip**。改了 `--description` 想重生成？加 `--regenerate-docs`。

### Phase 5 — Local git

`publish.py` 直接干（邮箱/身份的检查委托给 `check_git_config.py`）：

- 没 `.git/` 就 `git init -b main`
- `user.email` 像私人邮箱（gmail / outlook / qq 等）软提示一次——只警告不改
- `git add -A`
- `git commit -m "<message>"` —— 默认 `Initial commit`；工作树干净就跳过

### Pre-push review（不计编号）

push 前 `publish.py` 打印 Plan summary 块：

```
=== Pre-push review (re-run with --yes to confirm) ===
  Project path:    /path/to/my-tool
  Repo name:       my-tool
  Visibility:      Public
  License:         MIT
  Description:     ...
  Author:          ...
  Will create:     https://github.com/<author>/my-tool
```

退出码 12。**到这一步 GitHub 那边零改动。**

要继续？带 `--yes` 重跑同一条命令。

### Phase 6 — Create + push

调用 `create_repo_safe.py`。按顺序尝试 3 条路径：

| 路径 | 方式 | 适用 |
|---|---|---|
| A | `gh repo create … --push` | `gh` 装了并登录了 |
| B | `urllib` POST `/user/repos`，PAT 从 `git credential fill` 读，然后 `git push` | 没 `gh` 但钥匙串里有 PAT |
| C | 打印手把手网页教程，exit 13 | A 和 B 都不行 |

先做安全检查：如果 `origin` 已经指向别的 URL，拒绝（exit 4）并打印 3 个修复选项（手动 push / `--force-overwrite-origin` 替换 / `git remote remove origin` 重试）。**绝不静默覆盖你自己设的 remote。**

Token 处理（Path B）：PAT 通过 `git credential fill` 读取（停留在 OS 钥匙串机制内）→ 写入 0600 tempfile → 作为 HTTPS API 请求的 header → 用完 **用随机字节 shred + unlink 销毁**。永不进环境变量、永不进 stdout。

### Phase 7 — Verify

调用 `verify_remote.py`。做：

- `git fetch origin --quiet`
- 对比 `HEAD` 和 `origin/main` —— 必须一致
- `git ls-tree origin/main` —— 检查 `README.md` / `LICENSE` / `.gitignore` 都在远端

任何检查失败 → exit 1。全过 → 打印仓库 URL + 成功摘要。

---

## Exit code 一览

| Code | 含义 | 怎么处理 |
|---|---|---|
| 0 | 完成 —— 仓库已建好已验证 | 打开最后打印的 URL |
| 1 | 通用错误 | 看 log 找是哪个 phase 失败 |
| 4 | `origin` 已指向别的 URL（Path A/B 的安全检查） | 看打印的 hint：手动 push / `--force-overwrite-origin` / `git remote remove origin` |
| 10 | Preflight：必需工具缺失 | 按打印的命令装好重跑 |
| 11 | Scan：RED 发现 | 按 `references/secret-fix-recipes.md` 修了重跑 |
| 12 | Pre-push review（没 `--yes`） | 看 plan 没问题 → 加 `--yes` 重跑 |
| 13 | Auth 走到 Path C（手动） | 按打印的浏览器 + 终端步骤照做 |

---

## 常见场景

### "只想发布，全用默认"

```bash
python3 scripts/publish.py /path/to/folder
# 看 plan，再：
python3 scripts/publish.py /path/to/folder --yes
```

### "description 写错了 README 已经写进去了"

```bash
python3 scripts/publish.py /path/to/folder \
    --description "改正后" \
    --regenerate-docs
# （如果还在 push 前，再 --yes）
```

`--regenerate-docs` 会覆盖三个生成文件。**会覆盖你手动改过的 README/LICENSE/.gitignore**——手动改过先把改动保存出来。

### "提示走 Path C 要我手动操作"

Path C 只在 `gh` 和缓存 PAT 都没有时触发。教程很短（浏览器里 ~5 步，终端 1 条命令）。你可以：

- **现在**：照打印的步骤做（立即生效）
- **后续**：装 `gh` 然后 `gh auth login`，以后就走 Path A

### "想先 private 测试"

```bash
python3 scripts/publish.py /path/to/folder --private --yes
```

后续在 GitHub Settings → General → Danger Zone → Change visibility 翻成 public。

### "想用非 MIT 协议"

```bash
python3 scripts/publish.py /path/to/folder --license Apache-2.0
# 或
python3 scripts/publish.py /path/to/folder --license GPL-3.0
```

不知道选哪个看 [`references/license-chooser-newbie.md`](references/license-chooser-newbie.md)。拿不准选 MIT。

### "想重新 publish——已经有 commit 了"

如果项目已经是 git repo 且工作树没新东西，Phase 5 会打"nothing new to commit (working tree clean)" 并继续。GitHub 上仓库不存在 → Phase 6 建仓 + push。GitHub 上仓库已存在且 `origin` 指过去 → 撞 exit 4，自己 `git push -u origin main` 就行。

### "scan 误报了一个不是 secret 的字符串"

看下面 [`scan-ignore-file` 标记](#scan-ignore-file-标记)章节。如果只是一次性误报不想标到文件里，选择只有：

1. 重写那一行让正则不匹配（如假 key 中间插一个空格）
2. 把示例挪到一个专门的文档文件里，给那个文件加 marker

故意没设计 `--ignore-pattern` CLI 参数——"用户一锁定 pattern 忽略掉真泄漏"的代价太大。

---

## Fork 项目和第三方代码

### 项目是 fork

如果 `git remote -v` 含 `upstream`，或 manifest 文件（`package.json`、`pyproject.toml`）含 `forkedFrom`，Phase 2 标为 fork。Phase 3 的 attribution 扫描读 upstream URL。Phase 4 用 `with-fork-attribution.md` README 模板，顶部含占位：

```
> This is a fork of [{UPSTREAM_NAME}]({UPSTREAM_URL}). Original work by {UPSTREAM_AUTHOR}.
```

push 前要把方括号里的占位填好。generator 能探测 upstream URL，但 name/author 填不出来——你手填。

**License 兼容性**：fork 必须沿用 upstream license。不能 fork GPL 项目然后改成 MIT 重发。Phase 4 不自动强制，自己检查。

### 项目包含第三方代码

存在 `vendor/` / `third_party/` / `external/` / `deps/` 目录，或任何含 `LICENSE` 文件的子目录，Phase 3 都会记录，Phase 4 用 `with-acknowledgements.md` 模板。生成的 Acknowledgements 段会列每个位置 + `[需要你补全]` 标记——发布前补全 source URL 和作者。

那些子目录里的原 LICENSE 文件**保留不动**——Phase 4 只写一个顶层 `LICENSE` 给你自己的代码。

---

## `scan-ignore-file` 标记

有些文件就是为了文档化模式或修法存在的——比如列出示例 secret 字符串的参考文档、教你怎么修 secret 的教程。它们自身永远会被 scanner 自命中。

让 `scan_project.py` 跳过某个文件内容，在它**前 2 KB 内**放这个 marker：

```
<!-- scan-ignore-file: 一句话理由 -->
```

或 Python 文件里：

```python
# scan-ignore-file: 一句话理由
```

只要 marker 子串出现就行，注释格式不重要。skill 自己用了这个标记的有：`scripts/scan_project.py`（含自己的 pattern 源码）、`scripts/generate_files.py`（docstring 自然出现 "based on"）、3 个 reference 文档。

**慎用。** marker 意味着"信任这个文件的作者不会真粘 secret 进来"。别加给做正经事的源代码——只加给关于扫描自身的文档。

---

## 自定义模板

所有模板在 `references/` 下：

- `license-templates/{MIT,Apache-2.0,GPL-3.0}.txt` —— 法定文本含 `{YEAR}` / `{COPYRIGHT_HOLDER}` 占位
- `gitignore-templates/{python,node,shell,docs,general}.gitignore`
- `readme-templates/{basic,with-fork-attribution,with-acknowledgements}.md` —— `{占位符}` 由 `generate_files.py` 替换

加新语言 gitignore：把 `your-language.gitignore` 丢进 `gitignore-templates/`，再到 `scripts/generate_files.py` 的 `type_map` 加 `"your-language": "your-language.gitignore"`。

加新 license：把 `Your-License.txt` 丢进 `license-templates/`，含 `{YEAR}` 和 `{COPYRIGHT_HOLDER}` 占位，再到 `generate_files.py` 的 `generate_license()` 里 `tmpl_map` 加一条。

自定义 README 结构：直接改模板文件。占位符格式 `{LIKE_THIS}`。

---

## 单独跑每个脚本

不一定要用 `publish.py`。每个 phase 脚本都能单独跑：

```bash
# Phase 1: Preflight
python3 scripts/preflight.py

# Phase 2: Detect
python3 scripts/detect_project_type.py /path/to/folder

# Phase 3: Scan
python3 scripts/scan_project.py /path/to/folder
# 加 --format json 拿机器可读输出

# Phase 4: Generate
python3 scripts/generate_files.py /path/to/folder \
    --name my-tool --author xiaomoBoy \
    --license MIT --type python \
    --description "..." --tested-on "macOS and Windows"

# Phase 5（你自己干）：git init、git add、git commit
# Phase 4.5: check_git_config（被 publish.py 调用，也能单独跑）
python3 scripts/check_git_config.py /path/to/folder

# Phase 6: Create + push
python3 scripts/create_repo_safe.py /path/to/folder --name my-tool --public

# Phase 7: Verify
python3 scripts/verify_remote.py /path/to/folder
```

每个脚本的 `--help` 列出它完整的参数集。
