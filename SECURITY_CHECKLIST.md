# 🔒 安全检查清单

## ⚠️ 重要：这些文件绝对不能上传到 GitHub！

### ✅ 已配置忽略的文件类型

以下文件类型已经在 `.gitignore` 中配置，**不会**被提交到 GitHub：

#### 1. 环境变量和密钥文件
- ✅ `.env` - 包含 API 密钥、密码等敏感信息
- ✅ `.env.local` - 本地环境变量
- ✅ 任何包含密码、API key 的文件

#### 2. 数据库文件
- ✅ `*.db` - SQLite 数据库文件
- ✅ `*.sqlite` - SQLite 数据库
- ✅ `*.sqlite3` - SQLite 数据库
- ✅ `data/*.db` - 数据目录中的数据库

**为什么不能上传？**
- 数据库可能包含敏感数据
- 文件通常很大，不适合版本控制
- 每个环境应该有自己的数据库

#### 3. 大文件
- ✅ `data/nrdp_timetable/` - 时刻表数据目录
- ✅ `data/*.zip` - 压缩文件
- ✅ `data/timetable_parsed.json` - 解析后的时刻表（177MB）
- ✅ `data/*.MCA`, `*.ALF`, `*.DAT`, `*.FLF` - 时刻表原始文件

**为什么不能上传？**
- GitHub 限制单个文件最大 100MB
- 建议超过 50MB 的文件使用 Git LFS 或外部存储

#### 4. 其他敏感文件
- ✅ `*.key`, `*.pem`, `*.p12` - 密钥文件
- ✅ `*.log` - 日志文件（可能包含敏感信息）
- ✅ `__pycache__/` - Python 缓存
- ✅ `venv/`, `env/`, `.venv/` - 虚拟环境

---

## 📋 提交前检查清单

在每次 `git commit` 和 `git push` 之前，请检查：

### 1. 检查是否有敏感文件被意外添加

```bash
# 检查是否有 .env 文件
git ls-files | grep "\.env$"

# 检查是否有数据库文件
git ls-files | grep "\.db$"

# 检查是否有密钥文件
git ls-files | grep -E "\.(key|pem|p12)$"
```

**如果发现敏感文件，立即移除：**
```bash
git rm --cached <文件名>
git commit -m "Remove sensitive file"
```

### 2. 检查文件大小

```bash
# 检查是否有超过 50MB 的文件
find . -type f -size +50M -not -path "./.git/*" | head -10
```

### 3. 查看将要提交的文件

```bash
# 查看暂存区的文件
git status

# 查看详细的文件列表
git diff --cached --name-only
```

---

## 🚨 如果敏感文件已经被提交

### 情况 1: 刚刚提交，还没有 push

```bash
# 从提交中移除文件
git rm --cached <文件名>
git commit --amend
```

### 情况 2: 已经 push 到 GitHub

**立即采取行动：**

1. **从 Git 历史中移除文件**（需要强制推送）：
```bash
git rm --cached <文件名>
git commit -m "Remove sensitive file"
git push
```

2. **更改所有泄露的密钥/密码**：
   - 如果 `.env` 被提交，立即更改所有 API 密钥和密码
   - 通知相关服务提供商

3. **考虑使用 GitHub 的敏感数据扫描**：
   - GitHub 会自动扫描仓库中的敏感信息
   - 如果发现，会发送通知

---

## ✅ 当前状态检查

运行以下命令检查当前状态：

```bash
# 1. 检查是否有敏感文件在 Git 中
echo "=== 检查 .env 文件 ==="
git ls-files | grep "\.env$"

echo "=== 检查数据库文件 ==="
git ls-files | grep "\.db$"

echo "=== 检查密钥文件 ==="
git ls-files | grep -E "\.(key|pem|p12)$"

# 2. 检查被忽略的文件
echo "=== 被忽略的文件 ==="
git status --ignored | grep -E "\.(env|db|sqlite)$"

# 3. 检查大文件
echo "=== 检查大文件 (>50MB) ==="
find . -type f -size +50M -not -path "./.git/*" 2>/dev/null
```

---

## 📝 最佳实践

### 1. 使用 `.env.example` 作为模板

创建 `.env.example` 文件，包含所有需要的环境变量，但不包含实际值：

```bash
# .env.example
HSP_USERNAME=your_email@example.com
HSP_PASSWORD=your_password
DATABASE_URL=sqlite:///data/railfair.db
```

这个文件**可以**提交到 GitHub，作为配置参考。

### 2. 在 README 中说明环境变量

在 `README.md` 中说明需要哪些环境变量，以及如何配置。

### 3. 使用环境变量而不是硬编码

```python
# ❌ 不好
api_key = "sk-1234567890"

# ✅ 好
import os
api_key = os.getenv("API_KEY")
```

### 4. 定期检查 Git 历史

```bash
# 检查 Git 历史中是否有敏感信息
git log --all --full-history --source -- "*env*"
```

---

## 🔗 相关资源

- [GitHub 敏感数据扫描](https://docs.github.com/en/code-security/secret-scanning)
- [Git 最佳实践](https://git-scm.com/book/en/v2)
- [.gitignore 模板](https://github.com/github/gitignore)

---

## ✅ 当前配置状态

根据检查，以下文件**已经正确配置**为不提交：

- ✅ `.env` - 环境变量文件
- ✅ `data/railfair.db` - 主数据库
- ✅ `data/railfair_test.db` - 测试数据库
- ✅ `railfair_fares.db` - 票价数据库
- ✅ `data/nrdp_timetable/` - 时刻表目录
- ✅ `data/*.zip` - 压缩文件

**你的配置是安全的！** ✅

