# Phase 2 快速开始

## 🚀 启动 Phase 2

```bash
./run_phase2_background.sh
```

## 📊 监控状态

```bash
# 查看详细状态
./check_phase2.sh

# 实时监控（推荐）
./monitor_phase2.sh

# 或自定义刷新间隔（每5秒）
./monitor_phase2.sh 5
```

## 📝 查看日志

```bash
# 实时查看日志
tail -f logs/phase2_batch_*.log

# 查看最新日志文件
tail -f logs/phase2_batch_$(ls -t logs/phase2_batch_*.log | head -1 | xargs basename)
```

## 🛑 停止 Phase 2

```bash
./stop_phase2.sh
```

## ⚙️ Phase 2 配置

- **请求间隔**: 1-3秒（比 Phase 1 更快）
- **日期范围**: 2025-09-01 到 2025-10-31 (61天)
- **日期块**: ≤7天/块
- **预计时间**: 1-2小时（比 Phase 1 快 30-40%）

## 📋 完整命令列表

| 操作 | 命令 |
|------|------|
| 启动 | `./run_phase2_background.sh` |
| 检查状态 | `./check_phase2.sh` |
| 实时监控 | `./monitor_phase2.sh` |
| 查看日志 | `tail -f logs/phase2_batch_*.log` |
| 停止 | `./stop_phase2.sh` |

## 💡 提示

- Phase 2 使用更快的请求间隔（1-3秒），如果遇到限速可以调整回 2-3秒或 3-5秒
- 所有数据保存在同一个数据库：`data/railfair.db`
- 进度文件：`data/progress_phase2.json`
- 日志文件：`logs/phase2_batch_*.log`

