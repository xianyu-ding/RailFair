# 关闭 Terminal 指南

## ✅ 可以安全关闭 Terminal

所有后台进程都使用 `nohup` 运行，**即使关闭 terminal，进程也会继续运行**。

## 🔍 关闭 Terminal 后如何管理进程

### 1. 检查进程是否还在运行

**Phase 1:**
```bash
./check_phase1.sh
# 或
ps -p $(cat logs/phase1_batch_*.pid)
```

**Phase 2:**
```bash
./check_phase2.sh
# 或
ps -p $(cat logs/phase2_batch_*.pid)
```

### 2. 查看日志

**Phase 1:**
```bash
tail -f logs/phase1_batch_*.log
```

**Phase 2:**
```bash
tail -f logs/phase2_batch_*.log
```

### 3. 停止进程

**Phase 1:**
```bash
./stop_phase1.sh
```

**Phase 2:**
```bash
./stop_phase2.sh
```

### 4. 实时监控

**Phase 1:**
```bash
./monitor_phase1.sh
```

**Phase 2:**
```bash
./monitor_phase2.sh
```

## 📁 重要文件位置

即使关闭 terminal，这些文件仍然可用：

- **PID 文件**: `logs/phase1_batch_*.pid` 或 `logs/phase2_batch_*.pid`
- **日志文件**: `logs/phase1_batch_*.log` 或 `logs/phase2_batch_*.log`
- **进度文件**: `data/progress_phase1.json` 或 `data/progress_phase2.json`
- **数据库**: `data/railfair.db`

## 💡 提示

1. **关闭 terminal 前**，可以运行 `./check_phase1.sh` 或 `./check_phase2.sh` 确认进程正在运行
2. **重新打开 terminal 后**，直接运行检查脚本即可查看状态
3. **所有数据自动保存**，即使 terminal 关闭也不会丢失
4. **进程会继续运行**直到：
   - 所有任务完成
   - 手动停止（`./stop_phase1.sh` 或 `./stop_phase2.sh`）
   - 系统重启或进程崩溃

## 🔄 重新连接示例

```bash
# 1. 打开新的 terminal
# 2. 进入项目目录
cd /Volumes/HP\ P900/RailFair/uk-rail-delay-predictor

# 3. 检查进程状态
./check_phase1.sh
# 或
./check_phase2.sh

# 4. 查看实时日志
tail -f logs/phase1_batch_*.log
```

## ⚠️ 注意事项

- ✅ **可以安全关闭 terminal** - 进程会继续运行
- ✅ **数据自动保存** - 不会丢失进度
- ✅ **可以随时重新连接** - 使用检查脚本和日志文件
- ⚠️ **系统重启会停止进程** - 需要重新启动
- ⚠️ **如果进程崩溃** - 需要检查日志并重新启动

