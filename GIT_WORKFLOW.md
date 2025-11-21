# 📝 Git 工作流程指南

## 🚀 日常更新代码的步骤

每次修改代码后，按照以下步骤推送到 GitHub：

### 步骤 1: 查看更改

```bash
git status
```

这会显示：
- 哪些文件被修改了
- 哪些文件是新添加的
- 哪些文件被删除了

### 步骤 2: 添加文件到暂存区

#### 添加所有更改的文件：
```bash
git add .
```

#### 或者只添加特定文件：
```bash
git add 文件名
git add 目录名/
```

#### 添加多个文件：
```bash
git add 文件1 文件2 文件3
```

### 步骤 3: 提交更改

```bash
git commit -m "描述你的更改"
```

**提交信息示例：**
```bash
git commit -m "Update frontend API configuration"
git commit -m "Fix database connection issue"
git commit -m "Add new feature: route statistics"
git commit -m "Update documentation"
```

### 步骤 4: 推送到 GitHub

```bash
git push
```

如果这是第一次推送新分支，使用：
```bash
git push -u origin main
```

---

## 📋 完整示例

假设你修改了 `frontend/railfair/config.js`：

```bash
# 1. 查看更改
git status

# 2. 添加文件
git add frontend/railfair/config.js

# 3. 提交
git commit -m "Update API endpoint in frontend config"

# 4. 推送
git push
```

---

## ⚡ 快速命令（一行完成）

如果你想快速提交所有更改：

```bash
git add . && git commit -m "你的提交信息" && git push
```

**示例：**
```bash
git add . && git commit -m "Update frontend" && git push
```

---

## 🔍 常用命令

### 查看状态
```bash
git status                    # 查看工作区状态
git status --short            # 简短格式
```

### 查看更改内容
```bash
git diff                      # 查看未暂存的更改
git diff --staged             # 查看已暂存的更改
```

### 查看提交历史
```bash
git log                       # 查看提交历史
git log --oneline            # 单行显示
git log -5                    # 只显示最近5次提交
```

### 撤销更改
```bash
# 撤销工作区的更改（未暂存）
git restore 文件名

# 从暂存区移除文件（但保留工作区的更改）
git restore --staged 文件名

# 撤销最后一次提交（但保留更改）
git reset --soft HEAD~1
```

### 拉取最新代码
```bash
git pull                      # 从 GitHub 拉取最新代码
```

---

## 🚨 提交前检查清单

在 `git push` 之前，确保：

1. ✅ **没有敏感文件**（`.env`, `*.db` 等）
   ```bash
   git status
   ```

2. ✅ **没有大文件**（超过 50MB）
   ```bash
   find . -type f -size +50M -not -path "./.git/*"
   ```

3. ✅ **提交信息清晰**
   - 使用有意义的提交信息
   - 描述你做了什么更改

---

## 📝 提交信息规范

### 好的提交信息：
```bash
git commit -m "Add Netlify deployment configuration"
git commit -m "Fix CORS issue in API"
git commit -m "Update database schema documentation"
git commit -m "Remove sensitive data from config files"
```

### 不好的提交信息：
```bash
git commit -m "update"           # 太模糊
git commit -m "fix"              # 不清楚修复了什么
git commit -m "changes"          # 没有描述性
```

---

## 🔄 工作流程示例

### 场景 1: 更新前端配置

```bash
# 1. 修改文件
# 编辑 frontend/railfair/config.js

# 2. 查看更改
git status

# 3. 添加并提交
git add frontend/railfair/config.js
git commit -m "Update backend API URL in frontend config"
git push
```

### 场景 2: 添加新功能

```bash
# 1. 创建新文件
# 创建新功能文件

# 2. 添加所有新文件
git add .

# 3. 提交
git commit -m "Add new feature: route statistics API"

# 4. 推送
git push
```

### 场景 3: 修复多个文件

```bash
# 1. 修改多个文件
# 编辑多个文件

# 2. 查看所有更改
git status

# 3. 添加所有更改
git add .

# 4. 提交
git commit -m "Fix multiple bugs in API endpoints"

# 5. 推送
git push
```

---

## 🎯 记住这个流程

```
修改代码 → git add . → git commit -m "描述" → git push
```

---

## 💡 提示

1. **经常提交**：不要等到所有功能完成才提交，经常提交小的更改
2. **清晰的提交信息**：让其他人（和未来的你）知道每次提交做了什么
3. **提交前检查**：使用 `git status` 确保没有意外添加敏感文件
4. **定期拉取**：如果多人协作，定期运行 `git pull` 获取最新代码

---

## 🆘 遇到问题？

### 问题 1: "Your branch is ahead of 'origin/main'"
**解决**：运行 `git push`

### 问题 2: "Your branch is behind 'origin/main'"
**解决**：运行 `git pull` 拉取最新代码

### 问题 3: 推送被拒绝
**解决**：
```bash
git pull                    # 先拉取最新代码
# 解决冲突（如果有）
git push                    # 再推送
```

### 问题 4: 提交了敏感文件
**解决**：
```bash
git rm --cached 文件名      # 从 Git 中移除
git commit -m "Remove sensitive file"
git push
```

---

## 📚 更多资源

- [Git 官方文档](https://git-scm.com/doc)
- [GitHub 指南](https://guides.github.com/)

