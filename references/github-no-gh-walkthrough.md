# GitHub 网页手把手（没装 gh CLI 时用）

如果 `gh` 命令没装、`git credential` 里也没有可用 PAT，就走这条路。**完全在浏览器 + terminal 手动完成**，10 分钟内搞定。

## 一、创建空仓库（网页操作）

1. **打开** https://github.com/new （需要先登录 GitHub）

2. **填表单**：

   | 字段 | 填什么 |
   |---|---|
   | Repository name | `<你的仓库名>` |
   | Description | 项目一句话简介（可空，等会儿在 settings 改） |
   | Public / Private | **Public**（除非你想先私有测试） |
   | Add a README file | **不要勾**（本地已生成） |
   | Add .gitignore | **不要勾**（本地已生成） |
   | Choose a license | **不要勾**（本地已生成） |

3. **点底部绿色按钮 "Create repository"**

> ⚠️ README / .gitignore / LICENSE 三个 checkbox 一定**不要勾**。勾了 GitHub 会在仓库里先建这些文件，你本地 push 会冲突。

4. **创建完看到的页面**会显示三个 setup 选项：

   ```
   …or create a new repository on the command line
   …or push an existing repository from the command line
   ```

   找到 "**push an existing repository from the command line**"，会显示 2 行命令：

   ```
   git remote add origin git@github.com:<你的用户名>/<仓库名>.git
   git branch -M main
   git push -u origin main
   ```

5. **复制这 2 行命令，回到 terminal 在你的项目目录里跑**。

## 二、push 失败的几种情况 + 修法

### 2.1 `Permission denied (publickey)`

意思：SSH key 没配。两种修法：

**修法 A（最简单）**：换用 HTTPS 而不是 SSH

把上面 `git remote add origin` 那行换成：

```bash
git remote set-url origin https://github.com/<你的用户名>/<仓库名>.git
```

然后再 `git push -u origin main`，会弹出 GitHub 登录对话框，按提示输入用户名 + PAT（不是密码）。

**修法 B**：生成 SSH key 并加到 GitHub

```bash
# 生成 key（macOS / Windows 都能跑）
ssh-keygen -t ed25519 -C "你的邮箱"
# 一路回车，密码可空

# 复制公钥
cat ~/.ssh/id_ed25519.pub
```

打开 https://github.com/settings/keys → New SSH key → 粘贴 → Save。然后再跑 `git push`。

### 2.2 `Authentication failed`

意思：HTTPS 推送时密码不对。**GitHub 现在不用密码，要用 PAT（Personal Access Token）**：

1. 打开 https://github.com/settings/tokens/new
2. **Note**：填一个名字（比如"我的电脑"）
3. **Expiration**：90 days 或 No expiration
4. **Scopes**：至少勾 `repo`（推 / 拉私有公开仓都用这个）
5. 点底部 "Generate token"
6. **立刻复制 token**（关掉就再也看不到了）
7. 回到 terminal 重新 `git push`，提示输密码时粘贴 PAT

### 2.3 `Updates were rejected because the remote contains work that you do not have locally`

意思：GitHub 上仓库已经有东西了（多半因为你创建时勾了 README）。

修法：

```bash
git pull origin main --rebase
git push -u origin main
```

如果还是不行，最干净的办法是**删了 GitHub 上的仓重新建**（确认 checkbox 都不勾）。

### 2.4 `large file` 报错

意思：有文件超过 GitHub 100MB 限制。

修法：

```bash
# 找出大文件
find . -type f -size +50M -not -path "./.git/*"

# 加进 .gitignore（替换 <path>）
echo "<path>" >> .gitignore

# 从 staged 里移除
git rm --cached <path>
git commit -m "Remove large file from tracking"
git push -u origin main
```

## 三、push 成功后

终端会显示：

```
To github.com:<你的用户名>/<仓库名>.git
 * [new branch]      main -> main
branch 'main' set up to track 'origin/main'.
```

去浏览器打开 `https://github.com/<你的用户名>/<仓库名>` 应该能看到你的文件。

## 四、之后想做的事（手动 GitHub 操作）

回到仓库网页：

| 想做 | 在哪里点 |
|---|---|
| 加 description | 仓库主页右上 ⚙️ → "About" → Edit → Description |
| 加 topics | 同上 → Topics 字段，加几个关键词（如 `cli`, `python`, `tool`） |
| 开启 Issues / Discussions | Settings → 左侧 "General" → 下拉 "Features" → 勾选 |
| 改 visibility（Public ↔ Private） | Settings → 左侧 "General" → 下拉 "Danger Zone" |
| 删仓库 | Settings → 同上 Danger Zone → "Delete this repository" |

## 五、Windows 用户额外注意

- terminal 用 **PowerShell** 或 **Git Bash**（Git for Windows 自带），不要用 cmd.exe
- ssh-keygen / git 命令在 Git Bash 里跟 macOS 完全一样
- 如果 `cat ~/.ssh/id_ed25519.pub` 不工作，PowerShell 里用 `Get-Content $env:USERPROFILE\.ssh\id_ed25519.pub`
