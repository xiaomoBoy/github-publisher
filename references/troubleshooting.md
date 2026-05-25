# 常见报错 + 修法

按报错关键词查。

## Git push / 认证类

### `Permission denied (publickey)`

**原因**：用 SSH URL 推但 SSH key 没配。

**修法**：见 [github-no-gh-walkthrough.md §2.1](github-no-gh-walkthrough.md)

最快：把 remote URL 从 `git@github.com:` 换成 `https://github.com/`：

```bash
git remote set-url origin https://github.com/<user>/<repo>.git
```

### `Authentication failed for 'https://github.com/...'`

**原因**：HTTPS push 时密码不对。GitHub 现在不接受密码，要用 PAT。

**修法**：

1. 生成 PAT：https://github.com/settings/tokens/new → 勾 `repo` scope → 复制
2. 重试 `git push`，提示密码时粘贴 PAT（不是 GitHub 密码）

或者用 macOS keychain 一次性记住：

```bash
git config --global credential.helper osxkeychain
# Windows 用：git config --global credential.helper manager
```

### `Updates were rejected because the remote contains work...`

**原因**：远端有你本地没有的 commit（多半因为创仓库时勾了 README）。

**修法**：

```bash
git pull origin main --rebase
git push -u origin main
```

如果合并冲突一堆，最简单是**删了 GitHub 仓重新建**（确认创建时三个 checkbox 都不勾）。

### `fatal: remote origin already exists`

**原因**：`git remote add origin` 跑了两次。

**修法**：

```bash
git remote set-url origin <新 URL>   # 改而不是加
```

或者：

```bash
git remote remove origin
git remote add origin <URL>
```

### `Could not resolve host: github.com`

**原因**：网络问题（DNS / 防火墙 / 代理）。

**修法**：

```bash
ping github.com           # 看能不能通
curl https://github.com   # 看 HTTPS 能不能通
```

如果你用代理：

```bash
git config --global http.proxy http://127.0.0.1:7890
git config --global https.proxy http://127.0.0.1:7890
```

（端口换成你自己代理的）

不用代理后记得取消：

```bash
git config --global --unset http.proxy
git config --global --unset https.proxy
```

## Git config / 邮箱类

### Commit 之后才发现作者邮箱是私人邮箱

**预防**：Phase 4 的 `check_git_config.py` 会软提示。

**已经 commit 但没 push**：改最近一个 commit 的 author：

```bash
git commit --amend --author="Your Name <your-username@users.noreply.github.com>" --no-edit
```

也改未来所有 commit：

```bash
git config user.email "your-username@users.noreply.github.com"
git config user.name "Your Name"
```

**已经 push 过**：要重写 history（风险大），或者认了。隐私优先就重写：

```bash
# 用 git-filter-repo（pip install git-filter-repo）
git filter-repo --email-callback '
  return new_email if old_email == b"your-real@email.com" else old_email
'
git push --force-with-lease
```

⚠️ force push 危险，必须 `--force-with-lease` 而不是 `--force`。

## gh CLI 类

### `gh: command not found`

**修法**（按你系统）：

- macOS: `brew install gh`
- Windows: `winget install --id GitHub.cli` 或 `scoop install gh`

装完先 `gh auth login` 一次。

### `gh auth status` 显示 "You are not logged into any GitHub hosts"

**修法**：

```bash
gh auth login
```

按提示选 GitHub.com → HTTPS / SSH（推荐 SSH 如果你 SSH key 配过）→ 浏览器登录。

## 文件 / 大小类

### `remote: error: File X is XX.XX MB; this exceeds GitHub's file size limit of 100.00 MB`

**原因**：单文件超 100MB。

**修法**：

```bash
# 1. 加进 gitignore
echo "<path>" >> .gitignore

# 2. 从 staged / 历史里移除
git rm --cached <path>
git commit -m "Stop tracking large file"
git push -u origin main
```

如果**已经 commit 过**那个大文件（即使只在 staged 里），可能需要重写 history：

```bash
pip install git-filter-repo
git filter-repo --invert-paths --path <大文件路径>
git push --force-with-lease
```

大文件考虑用 [Git LFS](https://git-lfs.github.com/) 而不是塞 git。

### `error: pathspec '...' did not match any files`

**原因**：路径打错 / 文件不存在 / 文件被 gitignore 了。

**修法**：

```bash
ls path/to/file        # 文件存在吗
git status --ignored   # 列被忽略的文件
```

## Scan 类（本 skill 特有）

### Scan 一直报红警，但我已经改了

**修法**：scan 是按当前 working tree 扫的。改完要：

1. 文件确实存了
2. 重跑 scan：`python3 scripts/scan_project.py <project-path>`
3. 如果 secret 已经 commit 过（不在 working tree 但在 git history） → scan 不会扫 history，但**这个 secret 已经泄漏过了**，必须按 [secret-fix-recipes.md §git history](secret-fix-recipes.md#还原"已-commit-过的-secret") 处理

### Scan 误报了一个不是 secret 的字符串

**修法**：临时跳过这一次（极少用）：

```bash
python3 scripts/scan_project.py <path> --ignore-pattern "<误报的字符串>"
```

更稳的：把那个值改成不会被误报的形式（比如改个变量名 / 加注释说明它是 sample data）。

### Phase 1 选择 license 时不确定

**修法**：选 MIT。见 [license-chooser-newbie.md](license-chooser-newbie.md)。
