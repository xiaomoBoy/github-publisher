# Phase 6 可选 Add-ons

Phase 6 的完成 checklist 里列的「⚪ 可选」，用户说要就回来加。

## 1. 加 GitHub repo description + topics

**为什么**：description 决定别人搜索时显示什么；topics 让你的仓库出现在 GitHub Explore 的对应主题页。**对引流很关键**。

**做法**：

打开 `https://github.com/<user>/<repo>` → 右上 ⚙️（Settings 旁边的小齿轮）→ 编辑：

- **Description**：一句话讲项目做啥（30-100 字符）
- **Topics**：5-10 个关键词（Phase 0 探测的项目类型 + 你自己想到的）
- **Website**：项目主页（可空）

**自动建议 topics**（按项目类型）：

| 项目类型 | 建议 topics |
|---|---|
| Python lib | `python`, `library`, `cli` (若是 CLI), 领域词 |
| Node lib | `javascript` / `typescript`, `npm`, `library` |
| Shell scripts | `shell`, `bash`, `cli`, `automation` |
| Docs only | `documentation`, `guide`, 主题词 |
| Claude Code skill | `claude-code`, `claude-skills`, `agent-skills` |
| 通用 | 至少加项目语言 + 用途词 |

## 2. 打 v0.1.0 tag + 写 release notes

**为什么**：让别人能 `git clone --branch v0.1.0` 拉特定版本；GitHub Release 页面是个独立曝光面。

**做法**：

本地：

```bash
git tag -a v0.1.0 -m "Initial release"
git push origin v0.1.0
```

GitHub 网页：

1. 仓库主页 → 右侧 "Releases" → "Create a new release"
2. **Tag**: 选 `v0.1.0`
3. **Title**: `v0.1.0 — Initial release`
4. **Description**: 写 release notes。可以从 CHANGELOG.md 复制
5. 勾 "Set as the latest release"
6. 点 "Publish release"

## 3. 生成 CONTRIBUTING.md

**为什么**：告诉别人怎么贡献。哪怕没人来贡献，也显得专业。

**做法**：用 `references/readme-templates/contributing-basic.md` 模板，改改项目名 + 联系方式。

最低要包含：

- Issue 怎么提
- PR 怎么发
- 代码风格基本要求（或 "用 prettier / black 格式化即可"）
- License 声明（"By contributing, you agree your contribution is licensed under <license>"）

## 4. 生成 CHANGELOG.md

**为什么**：版本记录。即使你没规律发版，写一份能让别人知道项目还活着。

**做法**：

```markdown
# Changelog

## [Unreleased]

## [0.1.0] — YYYY-MM-DD

Initial release.

### Added

- 项目主功能
- ...

[Unreleased]: https://github.com/<user>/<repo>/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/<user>/<repo>/releases/tag/v0.1.0
```

格式参考 [Keep a Changelog](https://keepachangelog.com/)。

## 5. 添加 README badges

**为什么**：badges 在 README 顶部显示徽章（license、star 数、版本、CI 状态），让仓库看着更"在维护"。

**做法**：在 README 顶部加（替换 `<user>/<repo>`）：

```markdown
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Stars](https://img.shields.io/github/stars/<user>/<repo>?style=social)](https://github.com/<user>/<repo>)
[![Last commit](https://img.shields.io/github/last-commit/<user>/<repo>)](https://github.com/<user>/<repo>/commits/main)
[![Issues](https://img.shields.io/github/issues/<user>/<repo>)](https://github.com/<user>/<repo>/issues)
```

更多徽章去 https://shields.io/ 自选。**别加太多**，4-6 个够了，太多反而像虚张声势。

## 6. 加中文 README（双语）

**为什么**：如果你的目标用户里有中文使用者，多一个中文 README 转化率高很多。

**做法**：

1. 在英文 `README.md` 顶部加：
   ```markdown
   **中文版**: [README.zh-CN.md](README.zh-CN.md)
   ```

2. 复制 README.md 为 README.zh-CN.md，翻译内容
3. 在 zh-CN 版顶部加：
   ```markdown
   **English version**: [README.md](README.md)
   ```

可以让 Claude 直接翻译，或者你自己翻。

## 7. 开启 Discussions

**为什么**：Issues 适合 bug 报告，Discussions 适合"这个怎么用"、"有没有想法做 X" 这种讨论。降低用户来交流的门槛。

**做法**：

仓库主页 → Settings → 左侧 "General" → 下拉到 "Features" → 勾 ☑ Discussions → Save changes

## 8. 生成 .github/ISSUE_TEMPLATE 和 PR template

**为什么**：让别人提 issue / PR 时按模板填，省得他们不知道写啥、你看不懂他想说啥。

**做法**：

创建：

- `.github/ISSUE_TEMPLATE/bug_report.md`
- `.github/ISSUE_TEMPLATE/feature_request.md`
- `.github/ISSUE_TEMPLATE/config.yml`
- `.github/PULL_REQUEST_TEMPLATE.md`

模板可以从我们之前 claude-writing-skills 仓里拷（如果有），或者用 GitHub 默认模板：在 GitHub 仓库设置里点 "Set up templates" 一键生成。

## 9. 加 Claude Code marketplace 元数据

**条件**：只有你的项目里有 `SKILL.md` 文件时，这个 add-on 才有意义。

**为什么**：让别人能用 `/plugin marketplace add <user>/<repo>` 一键安装你的 skill。

**做法**：

创建 `.claude-plugin/marketplace.json`：

```json
{
  "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
  "name": "<your-skill-collection-name>",
  "description": "<一句话简介>",
  "owner": {
    "name": "<your-name>",
    "url": "https://github.com/<your-user>"
  },
  "plugins": [
    {
      "name": "<plugin-name>",
      "source": "./",
      "description": "<一句话>",
      "version": "0.1.0"
    }
  ]
}
```

和 `.claude-plugin/plugin.json`：

```json
{
  "name": "<plugin-name>",
  "version": "0.1.0",
  "description": "<同上>",
  "author": { "name": "<your-name>" },
  "repository": "https://github.com/<user>/<repo>",
  "license": "MIT",
  "keywords": ["claude-code", "claude-skills"]
}
```

具体字段参考 [Claude Code marketplace docs](https://docs.claude.com/en/docs/claude-code/plugin-marketplaces) 或 `anthropics/claude-plugins-official` 这个 marketplace 仓的格式。

## 10. INSTALL.md / INTEGRATIONS.md / docs/USAGE.md

**条件**：项目复杂，有多个依赖、多种用法、多个 runtime 支持时才需要。简单项目 README 写够就行。

详见对应模板（如果有 readme-templates/ 下没收的话，参考 claude-writing-skills 仓的对应文件）。

## 不在本 skill 范围的（即使用户要也别帮做）

- CI/CD (GitHub Actions / 别的)
- 发到 npm / pip / crates / homebrew 等包注册中心
- 写 launch 推文 / 分发到社交平台
- 改代码本身（重构 / 测试 / 性能）
- 跨平台兼容性测试

这些要么是独立的 task（找别的 skill），要么需要更多 context（让用户自己决定）。
