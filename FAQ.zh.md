# 常见问题

English → [FAQ.md](FAQ.md)

小白高频问题，大白话解释。每答案需要时给长文档链接。

- [我必须懂 git 才能用吗？](#我必须懂-git-才能用吗)
- [必须有 AI 助手吗？](#必须有-ai-助手吗)
- [我的真实邮箱会显示在每个 commit 上吗？](#我的真实邮箱会显示在每个-commit-上吗)
- [之后想删仓库怎么办？](#之后想删仓库怎么办)
- [Public 还是 Private 我该选哪个？](#public-还是-private-我该选哪个)
- [MIT / Apache 2.0 / GPL 怎么选？](#mit--apache-20--gpl-怎么选)
- [万一不小心 push 了 secret 怎么办？](#万一不小心-push-了-secret-怎么办)
- [这个工具收钱吗？会收集我的代码吗？](#这个工具收钱吗会收集我的代码吗)
- [Linux 能用吗？](#linux-能用吗)
- [能离线用吗？](#能离线用吗)
- [为什么默认 Public + MIT？](#为什么默认-public--mit)
- [发布了能撤销吗？](#发布了能撤销吗)
- [我项目已经是 git 仓库了，还能用吗？](#我项目已经是-git-仓库了还能用吗)

---

## 我必须懂 git 才能用吗？

**不用。** 工具替你跑 git 命令（`init` / `add` / `commit` / `push`），还自动处理 GitHub 鉴权（三路径兜底）。

出问题时工具会**打出确切的命令**让你复制粘贴——不需要凭记忆敲 git。[INSTALL.zh.md](INSTALL.zh.md) 和 [TROUBLESHOOTING.zh.md](TROUBLESHOOTING.zh.md) 覆盖少数你可能要手动跑的命令（比如设名字和邮箱）。

只有一件事必须自己做一次：设 git 身份：

```bash
git config --global user.name "你的名字"
git config --global user.email "you@example.com"
```

（没设的话 preflight 会用确切命令提醒你。）

## 必须有 AI 助手吗？

**不用。** AI 是可选的。用 Claude Code（或类似）你说"开源 `/path/to/project`"，AI 替你跑脚本。没 AI 你自己跑 `python3 scripts/publish.py /path/to/project`——同一套脚本，同一套流程。

脚本是 stdlib Python，可独立运行。见 [INSTALL.zh.md § 不用 AI 独立运行](INSTALL.zh.md#不用-ai-独立运行)。

## 我的真实邮箱会显示在每个 commit 上吗？

**默认会。** 你在 `git config user.email` 设的邮箱会进每个 commit，commit log 对任何拿到仓库 URL 的人都可见。

想保留邮箱隐私用 GitHub noreply 别名：

1. 去 <https://github.com/settings/emails> 找你的别名。格式 `<id>+<username>@users.noreply.github.com`。
2. 设上：

   ```bash
   git config --global user.email "<你的用户名>@users.noreply.github.com"
   ```

`preflight.py` 检测到你的邮箱像私人邮箱（gmail / outlook / qq 等）会给一句软警告——只警告不改。

完整说明：[INSTALL.zh.md § 邮箱隐私](INSTALL.zh.md#邮箱隐私)。

## 之后想删仓库怎么办？

工具故意不替你删远端仓库（自动化风险太大）。两种手动方式：

```bash
# gh CLI ——会让你打仓库名确认
gh repo delete <owner>/<repo>
```

或浏览器：打开你的仓库 → **Settings** → 拉到底部 **Danger Zone** → **Delete this repository**。

**注意**：删掉的公开仓库可能仍存在于：
- 搜索引擎的旧缓存 / wayback 类归档
- 仓库公开期间 clone 或 fork 过的人手里
- GitHub 自己的 fork 历史（fork 删了仓库也留）

如果担心的是 secret 泄漏，**去源头撤销 secret** 比删仓库更重要。见 [TROUBLESHOOTING.zh.md § 不小心 push 了 secret](TROUBLESHOOTING.zh.md#不小心-push-了-secret)。

## Public 还是 Private 我该选哪个？

**第一次开源默认 Public。** 理由：

- "开源"本意就是公开
- Public 仓库才有 GitHub Issues / Discussions / Pages / 免费 CI 分钟数 / 搜索索引
- 改主意了去 **Settings → Danger Zone → Change visibility** 翻

**Private** 适合：想先试推送流程 / 想分享给特定的人 / 还不确定代码够不够好。用 `--private`：

```bash
python3 scripts/publish.py /path/to/folder --private
```

## MIT / Apache 2.0 / GPL 怎么选？

**90% 第一次开源的人：MIT。** 最简单、最宽松、最常见。

简易决策树：

| 你在意 | 选 |
|---|---|
| 不知道 / 不在乎，要个 license 就行 | **MIT** |
| 担心被大公司白嫖然后专利反告 | Apache 2.0 |
| 想让任何人改你的代码也必须开源（"传染性"） | GPL 3.0 |
| 完全放进公有领域，不要求保留作者名 | Unlicense / CC0（很少选） |

详细理由见 [`references/license-chooser-newbie.md`](references/license-chooser-newbie.md)。

用 `--license` 覆盖：

```bash
python3 scripts/publish.py /path/to/folder --license Apache-2.0
```

## 万一不小心 push 了 secret 怎么办？

工具的 scanner 检测到已知模式的 secret（OpenAI keys / GitHub PATs / AWS keys / PEM 私钥等）会**拒绝**发布。设计上就是要在泄漏**之前**抓住最常见的几类。

如果真的有真 secret 上了 GitHub（比如 scanner 漏掉了你的自定义 token 格式，或者你 `--skip-preflight` 又忽略了警告）：

1. **立刻去源头撤销泄漏的 secret**（OpenAI dashboard / GitHub settings / AWS IAM 等）。这一步最重要。
2. 生成新 secret，更新本地配置。
3. 可选：用 [`git-filter-repo`](https://github.com/newren/git-filter-repo) 或 [BFG](https://rtyley.github.io/bfg-repo-cleaner/) 重写 history——但要明白 GitHub 可能缓存了泄漏的 commit，force-push 之前 clone 过的人还持有旧 history。

完整说明：[TROUBLESHOOTING.zh.md § 不小心 push 了 secret](TROUBLESHOOTING.zh.md#不小心-push-了-secret)、[SECURITY.zh.md](SECURITY.zh.md)。

## 这个工具收钱吗？会收集我的代码吗？

**都不会。**

- 免费开源（MIT 协议）。无订阅、无注册、无付费档。
- 完全在你本机跑。唯一的网络请求是：
  - `api.github.com` —— 检查连通性（preflight）和建仓（Phase 6，仅在你确认推送时）
  - `github.com` —— 实际 `git push`（Phase 6，仅在你确认推送时）
- 不 phone home，不追踪使用，不把你代码发到别处——只发到**你显式建的那个 GitHub 仓库**。
- 你用来驱动这工具的 Anthropic / OpenAI 等 AI 助手有它们自己的数据政策——那是分开的。发布脚本本身不调任何 AI 服务。

## Linux 能用吗？

**大概率能用，但不在测试矩阵里。** 所有脚本只用 Python stdlib + 标准 `git` / `gh` 命令，没理由跑不了。当前测试在 macOS 和 Windows 上过。Linux 上试了崩了请开 issue。

## 能离线用吗？

**部分可以。**

- Phase 1（preflight）—— 检查 `api.github.com` 连通性，离线会警告
- Phase 2, 3, 4, 5 —— 全本地，不联网
- Phase 6（建仓 + push）—— 要 `github.com` + `api.github.com` 通
- Phase 7（verify）—— 要 `github.com` 做 `git fetch`

离线状态可以跑到 Phase 5（用 `--no-push`）生成文件 + 做本地 commit。有网后再推。

```bash
python3 scripts/publish.py /path/to/folder --no-push
# 后续有网时：
python3 scripts/publish.py /path/to/folder --yes
```

## 为什么默认 Public + MIT？

两层"最不让小白意外的默认"：

- **Public**：这是"开源"工具，预期就是公开发布。默认 Private 跟名字相违。
- **MIT**：最常见、最简单的协议。没几段法律文，没专利 / copyleft 细节。最不容易给你或你用户带来下游法律疑问。

两个都只需一个 CLI flag 翻。默认是建议，不是固执。

## 发布了能撤销吗？

**本地可以：**

```bash
cd /path/to/folder
rm -rf .git LICENSE README.md .gitignore
```

撤销 Phase 4-5。源代码从未被碰过。

**远端**：见上面[§之后想删仓库怎么办](#之后想删仓库怎么办)。远端删是手动的，可能也清不掉缓存 / fork。

## 我项目已经是 git 仓库了，还能用吗？

**能。** 工具检测到 `.git/` 就跳过 `git init`。工作树没新东西，Phase 5 会打 "nothing new to commit" 并继续。`--yes` 时还会推送。

**不会自动做的事**：往一个你已经配过、指向不同 URL 的 `origin` 推。Phase 6 安全检查会 exit 4，错误信息给三个选项（包括 `--force-overwrite-origin`）。

只是想推一个已配置好的仓库？可以跳过这工具自己 `git push -u origin main`。

---

问题不在这？看 [TROUBLESHOOTING.zh.md](TROUBLESHOOTING.zh.md) 或去 <https://github.com/xiaomoBoy/github-publisher/issues> 开 issue。
