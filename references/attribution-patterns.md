<!-- scan-ignore-file: this is the reference doc that *describes* attribution patterns; if scanned, every keyword in the list (Adapted from / Based on / @author / ...) self-matches. -->

# Attribution / 版权扫描规则

`scripts/scan_project.py` 的版权扫描部分。检测项目是否：
- 是别人项目的 fork
- 包含第三方代码
- 有显式 attribution 注释（已经在归属）

任一检测到 → **不是红警**（不阻断），但会让 Phase 3 自动在 README 加对应段落，提示用户补全。

## 一、Fork 信号

按可靠性从高到低：

### 1.1 git remote 含 upstream

```bash
git remote -v
# 如果输出里有 upstream，大概率是 fork
```

更可靠的判定：

```bash
# fork 的 origin URL 跟 upstream URL 不同
git remote get-url origin
git remote get-url upstream
```

### 1.2 manifest 文件里的 fork 标识

| 文件 | 字段 |
|---|---|
| `package.json` | `"forkedFrom"` / `"upstream"` / repository 字段指向别处 |
| `pyproject.toml` | `[tool.poetry.urls]` 里有 `upstream` |
| `Cargo.toml` | `repository` 字段指向别人仓库 |
| 任何文件 | `# Fork of <URL>` 或 `# Forked from <URL>` 这类注释 |

### 1.3 README 现有声明

如果项目 README 里已经写过 "Fork of X" / "Based on X"，记录下来用户已经做过 attribution，Phase 3 不重复加。

## 二、第三方代码

### 2.1 目录名 patterns

下面的目录名典型是放第三方代码的：

```
vendor/
third_party/
3rdparty/
external/
deps/
lib/        (含子目录有 LICENSE 时)
external-libs/
```

**例外（不算第三方）**：
- 这些目录已经在 `.gitignore` 里（说明不上传）
- 是用户自己代码的合理命名（如 `lib/utils.py` 跟模块同名）

### 2.2 子目录含 LICENSE 文件

任何子目录里有 `LICENSE` / `LICENSE.txt` / `LICENSE.md` / `COPYING` / `NOTICE` 这种**就是第三方代码的强信号**。这些文件不要删，README 要加 Acknowledgements 提到。

### 2.3 NOTICE / ATTRIBUTION 文件

项目根目录或子目录的 `NOTICE` / `NOTICE.txt` / `ATTRIBUTION` 文件本身就是 attribution 文档，记录在案。

## 三、代码注释里的 attribution 关键词

扫这些 patterns（case-insensitive）：

```
Adapted from
Based on
Derived from
Original by
Originally written by
@author       (JSDoc / JavaDoc 风格)
Credits?:
Copyright (c)  / Copyright ©  / © 20\d\d
Modified from
Inspired by   (弱信号，但记录)
Fork of
Borrowed from
```

**例外（不算 attribution）**：
- 出现在 LICENSE / 头部 license header 里（那是 license 本身）
- 出现在测试数据 / fixture / docs 里且明显是示例

## 四、自动处理逻辑

| 检测到 | Phase 3 自动动作 |
|---|---|
| Fork 信号（git remote / manifest） | README 顶部加 quote block: `> This is a fork of <upstream URL>. Original work by <提取的作者，不确定时用占位符 [Original Author]>.` |
| 第三方代码目录（vendor/ 等） | README 末尾加 `## Acknowledgements` 段落，列出每个目录 + 其 LICENSE 文件路径 |
| 子目录含 LICENSE | 同上，加进 Acknowledgements |
| 注释关键词 | 在 Phase 2 报告里列出，让 Claude 在 Phase 3 写 Acknowledgements 时**提示用户补全**（不替用户编作者名，留 `[需要补全]` 占位）|

## 五、用户必须补全的部分

skill 自动加段落只是骨架，下面这些必须用户人工补：

- Fork 的 upstream URL（如果只检测到 git remote 没 upstream URL，让用户提供）
- 第三方代码的真实出处（如 vendor/ 下的库叫什么、从哪来）
- 注释里 "Adapted from" 没说明白来源时，让用户补 URL

skill 在输出里要明确标 `[需要你补全]`，不替用户编造作者 / URL（编错了反而比不写更糟）。

## 六、输出格式（接到 scan_project.py 输出）

```json
{
  "attribution": {
    "is_fork": true,
    "fork_signals": [
      {"type": "git_remote_upstream", "url": "https://github.com/original/repo.git"},
      {"type": "manifest_forkedFrom", "file": "package.json", "value": "..."}
    ],
    "third_party_dirs": [
      {"dir": "vendor/lodash", "has_license": true, "license_file": "vendor/lodash/LICENSE"}
    ],
    "attribution_comments": [
      {"file": "src/utils.py", "line": 23, "match": "# Adapted from https://stackoverflow.com/a/12345"}
    ]
  }
}
```
