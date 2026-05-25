<!-- scan-ignore-file: this is a reference document that intentionally contains example secret/path patterns; scan_project.py should not flag content here as a real leak. -->

# Private Data Scan Patterns

`scripts/scan_project.py` 的扫描清单。任一命中算 **红警**，必须处理后才能继续。

## 一、个人路径硬编码

跨 Win/Mac 的硬编码用户目录都要扫：

| 平台 | Regex | 例子 |
|---|---|---|
| macOS | `/Users/[^/\s'\"]+` | `/Users/zp/.../config.py` |
| Linux | `/home/[^/\s'\"]+` | `/home/alice/project` |
| Windows | `C:\\Users\\[^\\\\\s'\"]+` | `C:\Users\Bob\AppData` |
| Windows (forward slash) | `C:/Users/[^/\s'\"]+` | `C:/Users/Bob/.config` |
| 主目录通配 | `\$HOME/[^\s'\"]+` 仅在配置文件 / 字符串字面量 | 视情况而定 |

**例外（不算红警）**：
- 出现在 `.gitignore` 里
- 出现在 README / docs 的示例代码块里且明显是说明（如 `<your-username>`）
- 出现在测试 fixture 里且用通用占位符

## 二、Secret patterns

### 2.1 强 secret（一律红警，无例外）

| 厂商 | Regex | 备注 |
|---|---|---|
| OpenAI | `sk-(proj-)?[A-Za-z0-9]{20,}` | 开头 `sk-` 或 `sk-proj-` |
| Anthropic | `sk-ant-[A-Za-z0-9\-_]{20,}` | |
| GitHub PAT (classic) | `ghp_[A-Za-z0-9]{36}` | |
| GitHub PAT (fine-grained) | `github_pat_[A-Za-z0-9_]{82}` | |
| GitHub OAuth | `gho_[A-Za-z0-9]{36}` | |
| AWS Access Key | `AKIA[0-9A-Z]{16}` | |
| AWS Secret | 难以正则准确匹配，靠 `aws_secret_access_key` 关键词 | |
| Slack Bot Token | `xoxb-[0-9]+-[0-9]+-[A-Za-z0-9]+` | |
| Slack User Token | `xoxp-[0-9]+-[0-9]+-[0-9]+-[a-z0-9]+` | |
| Google API Key | `AIza[0-9A-Za-z\-_]{35}` | |
| Stripe Live | `sk_live_[A-Za-z0-9]{24,}` | |
| Stripe Test | `sk_test_[A-Za-z0-9]{24,}` | 测试 key 也别上传 |
| SSH 私钥头 | `-----BEGIN (RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----` | |
| PGP 私钥 | `-----BEGIN PGP PRIVATE KEY BLOCK-----` | |
| Generic Bearer | `[Bb]earer\s+[A-Za-z0-9\-_\.]{20,}` | 容易误报，慎用 |

### 2.2 弱 secret（疑似，让用户确认）

- 形如 `password\s*=\s*['"][^'"\s]{6,}['"]` 的赋值
- 形如 `token\s*=\s*['"][^'"\s]{16,}['"]` 的赋值
- 形如 `api_key\s*=\s*['"][^'"\s]{16,}['"]` 的赋值
- `.env` 文件里的非空赋值

弱 secret 命中 → 让用户确认是不是真的 secret，是 → 红警，否 → 放行。

## 三、敏感文件名（直接根据文件名拦）

文件名匹配下面任意一项 → 红警（不管内容）：

```
.env
.env.local
.env.production
.env.development
*.key
*.pem
*.pfx
*.p12
id_rsa
id_rsa.pub      # pub 也别传，泄露身份
id_dsa
id_ecdsa
id_ed25519
id_ed25519.pub
credentials.json
credentials.yaml
secrets.json
secrets.yaml
.aws/credentials
.npmrc          # 可能含 npm token
.pypirc         # 可能含 PyPI 凭据
config.local.*
*.tfstate       # Terraform state 可能含 secret
*.tfvars
.netrc
```

**例外**：
- `.env.example` / `.env.template` / `.env.sample` 是模板文件，不算（但要验证内容确实是占位符）
- README / docs 里提到的"应该有 .env 文件"是说明，不算

## 四、扫描范围

**扫**：
- 所有 tracked 文件（git status 看到的）
- 所有 working tree 文件（不管 ignore 没 ignore，扫一遍）

**不扫**：
- `.git/` 内部（git 自己的 metadata）
- `node_modules/` / `venv/` / `.venv/` / `__pycache__/` / `dist/` / `build/`（第三方 / 构建产物）
- 二进制文件（`.png` / `.jpg` / `.zip` / `.exe` 等）

**git history** 不扫（这个 skill 不做，但应该在扫描报告末尾给一句提示："本次未扫 git history，如果你之前 commit 过 secret，需要单独处理 → 推荐用 `git-filter-repo` 或 BFG"）。

## 五、输出格式

`scan_project.py` 输出 JSON：

```json
{
  "status": "red" | "yellow" | "green",
  "summary": {
    "files_scanned": 123,
    "private_paths": 3,
    "strong_secrets": 1,
    "weak_secrets": 2,
    "sensitive_files": 1,
    "attribution_signals": 0,
    "large_files": 0
  },
  "findings": [
    {
      "category": "strong_secret",
      "type": "openai",
      "file": "src/config.py",
      "line": 14,
      "match_preview": "sk-...redacted...",
      "fix_hint": "→ 见 references/secret-fix-recipes.md §1"
    },
    ...
  ]
}
```

`status` 为 `red`（有任一红警）/ `yellow`（仅弱 secret 待确认）/ `green`（全过）。
