<!-- scan-ignore-file: this is a fix-recipe document that intentionally contains example secret strings; scan_project.py should not flag content here as a real leak. -->

# Secret 修法 Recipes

`scan_project.py` 扫到 secret 时，按下面对症修。**skill 给修法，但不替用户改代码**。

## 总原则

1. **真值移到环境变量 / 本地配置文件**
2. **本地配置文件加进 `.gitignore`**
3. **代码里改成读环境变量 / 本地文件**
4. **提供一份 `.env.example` / `config.example.json` 让别人知道要配什么**

## §1 OpenAI / Anthropic / LLM API key

### 翻车的代码

```python
# 配置文件 / 源码里写死
OPENAI_API_KEY = "sk-proj-AAAAbbbbCCCCddddEEEEffff"
```

### 修法

```python
import os
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY env var not set")
```

把真值写到 `.env`（**先确认 `.env` 在 `.gitignore` 里**）：

```bash
echo "OPENAI_API_KEY=sk-proj-AAAA..." > .env
echo ".env" >> .gitignore
```

提供模板让别人知道要配：

```bash
cat > .env.example <<EOF
OPENAI_API_KEY=sk-...your-key-here...
EOF
```

如果是 Node 项目用同样思路 + `dotenv` 包：

```javascript
require('dotenv').config()
const apiKey = process.env.OPENAI_API_KEY
```

## §2 GitHub PAT (`ghp_...` / `github_pat_...`)

### 翻车的代码

```python
GITHUB_TOKEN = "ghp_AAAAbbbbCCCC..."
```

### 修法

跟 §1 一样，移到 env：

```python
import os
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
```

**额外**：去 https://github.com/settings/tokens **撤销这个 token**（点 Delete），生成新的。**已经 commit 过的 token 必须当作泄漏处理**。

## §3 AWS Access Key

### 翻车的代码

```python
AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"
AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
```

### 修法

不要写在代码里。AWS SDK 自动从这些地方找凭据（按顺序）：

1. 环境变量 `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`
2. `~/.aws/credentials`（用 `aws configure` 一次性配好）
3. IAM role（在 EC2 / Lambda 上）

代码完全不需要写 key：

```python
import boto3
s3 = boto3.client("s3")  # 自动找凭据
```

**已经 commit 过的 key 必须**去 AWS Console → IAM → Users → 你的用户 → Security credentials → 删掉那个 access key 重新生成。

## §4 SSH 私钥（`id_rsa` / `-----BEGIN PRIVATE KEY-----`）

### 翻车的情况

误把 `~/.ssh/id_rsa` 复制进了项目目录，或者代码里塞了 private key 字符串。

### 修法

1. 把私钥文件从项目里删（**不是删原 `~/.ssh/id_rsa`**）：
   ```bash
   rm path/to/leaked/id_rsa
   ```

2. 加进 `.gitignore`：
   ```bash
   echo "id_rsa" >> .gitignore
   echo "id_*" >> .gitignore
   echo "*.pem" >> .gitignore
   echo "*.key" >> .gitignore
   ```

3. **如果这个 key 已经被 commit 过**：当作泄漏处理 → 把 GitHub 上所有用这个 key authenticate 过的服务都换 key（**通常意味着重新生成 ssh key 并加到所有 server**）

## §5 数据库连接字符串

### 翻车的代码

```python
DB_URL = "postgresql://user:my_real_password@prod.db.example.com:5432/mydb"
```

### 修法

```python
import os
DB_URL = os.getenv("DATABASE_URL")
```

`.env`:
```
DATABASE_URL=postgresql://user:my_real_password@prod.db.example.com:5432/mydb
```

`.env.example`:
```
DATABASE_URL=postgresql://user:password@host:5432/dbname
```

## §6 `.env` 文件本身被 commit 了

### 翻车

```bash
$ git status
modified: .env
```

### 修法

```bash
# 从 git 里移除（保留本地文件）
git rm --cached .env

# 加进 gitignore
echo ".env" >> .gitignore

# 提交
git add .gitignore
git commit -m "Stop tracking .env"
```

**已经 push 过的 .env** 必须当作泄漏处理 → 里面所有 secret 都要轮换。

## §7 个人路径硬编码（`/Users/xxx`）

### 翻车的代码

```python
DATA_DIR = "/Users/zp/Documents/myproject/data"
```

### 修法 A（如果是配置）

用环境变量或 CLI 参数：

```python
import os
from pathlib import Path
DATA_DIR = Path(os.getenv("DATA_DIR", "./data")).resolve()
```

### 修法 B（如果是相对项目根）

```python
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
```

### 修法 C（如果在文档 / 示例里）

文档里改成占位符：

```markdown
# 不要写
DATA_DIR=/Users/zp/Documents/myproject/data

# 改成
DATA_DIR=/path/to/your/data
```

## §8 通用兜底（不知道怎么改）

如果某个 secret 你不知道怎么改，**先让代码继续能跑**：

1. 临时把那行注释掉
2. 加一个 TODO：`# TODO: move to env var, see references/secret-fix-recipes.md`
3. 在 README 加一段「Setup → Required environment variables」列出要配什么
4. 跑 `scan_project.py` 验证已经不再红警

完美永远不可能，**先不再泄漏**是第一步。

## 还原"已 commit 过的 secret"

**git history 里的 secret 一旦 push 过就不能假装没发生**。即使你下个 commit 删了，旧 commit 里还能看到。

对策：
- **最重要**：去对应服务（OpenAI / GitHub / AWS / etc）撤销这个 secret，生成新的
- **次重要**：用 [`git-filter-repo`](https://github.com/newren/git-filter-repo) 或 [BFG Repo-Cleaner](https://rtyley.github.io/bfg-repo-cleaner/) 改写 git history（但已经 push 到 GitHub 的话，缓存里可能还在）
- **预防**：以后 commit 前用 [`gitleaks`](https://github.com/gitleaks/gitleaks) 之类的 pre-commit hook

本 skill 不做 history 重写，因为风险大。请用上面专门工具或求助有经验的人。
