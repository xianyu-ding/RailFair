# 🐍 虚拟环境使用指南

## ✅ 环境已创建

你的虚拟环境 `railenv` 已经使用 **Conda** 创建并配置完成！

## 🚀 激活环境

每次使用项目时，需要先激活环境：

```bash
conda activate railenv
```

激活后，你的终端提示符会显示 `(railenv)`，表示环境已激活。

## 📦 已安装的依赖

所有 `requirements.txt` 中的依赖都已安装，包括：
- FastAPI
- Uvicorn
- SQLAlchemy
- Pandas, NumPy, Scikit-learn
- Redis
- 以及其他所有必需的包

## 💻 使用环境

### 运行 API 服务器

```bash
# 激活环境
conda activate railenv

# 运行 API
python api/app.py
```

### 运行其他脚本

```bash
# 激活环境
conda activate railenv

# 运行任何 Python 脚本
python predictor.py
python fetch_hsp.py
# ... 等等
```

## 🔄 退出环境

当你完成工作后，可以退出环境：

```bash
conda deactivate
```

## ⚠️ 重要提示

### 为什么使用 Conda 而不是 venv？

由于项目路径中包含特殊字符（空格），使用 Python 的 `venv` 模块可能会遇到编码问题。Conda 环境可以更好地处理这种情况。

### 环境位置

Conda 环境存储在：
```
/Users/vanessa/anaconda3/envs/railenv
```

这个路径不在项目目录中，所以：
- ✅ 不会被 Git 提交（已经在 `.gitignore` 中）
- ✅ 不会占用项目空间
- ✅ 可以在多个项目间共享（如果需要）

### 更新依赖

如果 `requirements.txt` 更新了，重新安装依赖：

```bash
conda activate railenv
pip install -r requirements.txt --upgrade
```

### 删除环境（如果需要）

如果环境出现问题，可以删除并重新创建：

```bash
conda deactivate  # 先退出环境
conda env remove -n railenv
conda create -n railenv python=3.9 -y
conda activate railenv
pip install -r requirements.txt
```

## 📝 快速参考

```bash
# 激活环境
conda activate railenv

# 检查 Python 版本
python --version

# 检查已安装的包
pip list

# 运行 API
python api/app.py

# 退出环境
conda deactivate
```

## 🎉 完成！

现在你可以正常使用项目了！每次打开新的终端窗口时，记得先运行 `conda activate railenv`。

