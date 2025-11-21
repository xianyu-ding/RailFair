# Phase 1 数据收集指南

## 概述

Phase 1 使用**少量多次**的策略收集冬季历史数据：
- ✅ **日期拆分**: 62天拆分为 ≤7天的小块（约9个chunks）
- ✅ **请求间隔**: 每次请求间隔 3-5秒（随机）
- ✅ **不增大请求量**: 保持小日期范围，避免超时和限速

### 数据范围
- **日期**: 2024-12-01 到 2025-01-31 (62天)
- **路由**: 10条主要铁路线路
- **天数类型**: WEEKDAY, SATURDAY, SUNDAY
- **总chunks**: ~270个 (10路由 × 3天数类型 × 9日期chunks)
- **预计时间**: 2-4小时

## 快速开始

### 1. 启动 Phase 1 收集（后台）

```bash
./run_phase1_background.sh
```

这将：
- 在后台启动数据收集进程
- 自动拆分日期范围为 ≤7天的块
- 每次请求间隔 3-5秒
- 保存日志到 `logs/phase1_batch_*.log`
- 保存进度到 `data/progress_phase1.json`

### 2. 检查状态

```bash
# 查看详细状态
./check_phase1.sh

# 实时监控（每10秒刷新）
./monitor_phase1.sh

# 或自定义刷新间隔（每5秒）
./monitor_phase1.sh 5
```

### 3. 查看日志

```bash
# 实时查看日志
tail -f logs/phase1_batch_*.log

# 查看最新日志文件
tail -f logs/phase1_batch_$(ls -t logs/phase1_batch_*.log | head -1 | xargs basename)
```

### 4. 停止收集

```bash
# 优雅停止（等待当前请求完成）
./stop_phase1.sh

# 或手动停止（如果知道PID）
kill <PID>
```

## 工作流程

### 日期拆分示例

对于 2024-12-01 到 2025-01-31 (62天)：

```
Chunk 1: 2024-12-01 to 2024-12-07 (7天)
Chunk 2: 2024-12-08 to 2024-12-14 (7天)
Chunk 3: 2024-12-15 to 2024-12-21 (7天)
...
Chunk 9: 2025-01-25 to 2025-01-31 (7天)
```

### 请求流程

对于每个路由和天数类型：

1. **路由 1 (EUS-MAN) - WEEKDAY**
   - Chunk 1: 请求 → 等待 3-5秒
   - Chunk 2: 请求 → 等待 3-5秒
   - ...
   - Chunk 9: 请求 → 等待 3-5秒

2. **路由 1 (EUS-MAN) - SATURDAY**
   - 重复上述流程

3. **路由 1 (EUS-MAN) - SUNDAY**
   - 重复上述流程

4. **路由 2 (KGX-EDR) - WEEKDAY**
   - 继续...

### 进度跟踪

进度自动保存到 `data/progress_phase1.json`：

```json
{
  "started_at": "2024-12-01T10:00:00",
  "last_updated": "2024-12-01T11:30:00",
  "completed_routes": ["EUS-MAN", "KGX-EDR"],
  "failed_routes": [],
  "total_records": 1234
}
```

## 监控命令

### 查看数据库统计

```bash
# 查看记录数
sqlite3 data/railfair.db "SELECT COUNT(*) FROM hsp_service_metrics;"
sqlite3 data/railfair.db "SELECT COUNT(*) FROM hsp_service_details;"

# 查看最近收集的数据
sqlite3 data/railfair.db "SELECT * FROM hsp_service_metrics ORDER BY fetch_timestamp DESC LIMIT 10;"
```

### 查看进度详情

```bash
# 使用 Python 格式化输出
cat data/progress_phase1.json | python3 -m json.tool
```

### 检查进程资源使用

```bash
# 查看 CPU 和内存使用
ps -p $(cat logs/phase1_batch_*.pid) -o pid,pcpu,pmem,etime,cmd
```

## 预期行为

### 正常运行时

1. **日期拆分信息**:
   ```
   📅 Date range split into 9 chunks (≤7 days each)
   ```

2. **请求间隔**:
   ```
   🔍 Chunk 1/27: WEEKDAY (2024-12-01 to 2024-12-07)
   Rate limiting: sleeping for 3.45s
   ✅ Found 25 services
   ```

3. **进度更新**:
   ```
   📊 Progress: 100 records saved
   ✅ Route EUS-MAN completed: 150 records saved
   ```

### 完成时

```
📊 COLLECTION SUMMARY
========================================
Routes Processed: 10/10
Routes Failed: 0
Total Records: 12,345
Total Time: 3h 45m
```

## 故障处理

### 进程意外停止

1. **检查日志**:
   ```bash
   tail -n 50 logs/phase1_batch_*.log
   ```

2. **检查进度**:
   ```bash
   cat data/progress_phase1.json
   ```

3. **重新启动**（会自动跳过已完成的路由）:
   ```bash
   ./run_phase1_background.sh
   ```

### 网络超时

如果遇到超时：
- 代码会自动重试（最多3次）
- 如果某个chunk失败，会继续下一个chunk
- 不会中断整个收集过程

### 限速问题

如果遇到限速：
- 请求间隔已经是 3-5秒（随机）
- 如果仍然被限速，可以手动增加间隔（修改 `fetch_hsp_batch.py` 中的 `min_request_interval` 和 `max_request_interval`）

## 性能优化

### 当前设置

- ✅ 日期拆分: ≤7天（避免超时）
- ✅ 请求间隔: 3-5秒（避免限速）
- ✅ 超时设置: 180秒（足够处理小日期范围）
- ✅ 自动重试: 最多3次（处理临时错误）

### 不建议修改

- ❌ **不要增大日期范围**: 保持 ≤7天以避免超时
- ❌ **不要减少请求间隔**: 3-5秒是安全间隔
- ❌ **不要并行运行**: 可能导致限速

## 数据验证

收集完成后，验证数据：

```bash
# 检查记录数
sqlite3 data/railfair.db << EOF
SELECT 
    COUNT(*) as total_metrics,
    COUNT(DISTINCT origin || '-' || destination) as unique_routes,
    MIN(fetch_timestamp) as first_collected,
    MAX(fetch_timestamp) as last_collected
FROM hsp_service_metrics;
EOF

# 检查每个路由的记录数
sqlite3 data/railfair.db << EOF
SELECT 
    origin || '-' || destination as route,
    COUNT(*) as records
FROM hsp_service_metrics
GROUP BY origin, destination
ORDER BY records DESC;
EOF
```

## 下一步

Phase 1 完成后：
1. 验证数据完整性
2. 检查数据质量
3. 准备 Phase 2（最近数据）或 Phase 3（夏季数据）

## 注意事项

⚠️ **重要提示**:
- 进程会在后台运行，即使关闭终端也会继续
- 使用 `./stop_phase1.sh` 优雅停止，不要直接 kill
- 定期检查日志确保没有错误
- 确保有足够的磁盘空间（预计 ~100MB 数据）

