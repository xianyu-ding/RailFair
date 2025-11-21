# Batch Collection 测试指南

## 快速开始

### 1. 后台运行测试

```bash
# 使用默认测试配置（7天，1个路由）
./test_batch_background.sh

# 或指定其他配置文件
./test_batch_background.sh configs/hsp_config_phase1.yaml
```

### 2. 查看运行状态

```bash
# 查看进程状态和最新日志
./check_test_batch.sh

# 实时查看日志
tail -f logs/test_batch_*.log

# 或查看最新的日志文件
tail -f logs/test_batch_$(ls -t logs/test_batch_*.log | head -1 | xargs basename)
```

### 3. 停止后台进程

```bash
# 自动查找并停止最新进程
./stop_test_batch.sh

# 或指定PID文件
./stop_test_batch.sh logs/test_batch_20241201_120000.pid
```

## 测试配置说明

### `configs/hsp_config_test.yaml`
- **日期范围**: 7天 (2024-10-01 到 2024-10-07)
- **路由**: 1个 (EUS-MAN)
- **天数类型**: WEEKDAY 仅
- **时间窗口**: 07:00-09:00 (早高峰)

这个配置可以快速验证：
- ✅ 日期范围拆分（应该创建1个7天的chunk）
- ✅ 请求间隔控制（3-5秒）
- ✅ 数据收集和保存
- ✅ 错误处理

## 手动运行（前台）

如果想在前台运行并看到实时输出：

```bash
python3 fetch_hsp_batch.py configs/hsp_config_test.yaml --phase "TEST"
```

## 使用其他配置

### 测试更长的日期范围

```bash
# 创建14天的测试（会拆分成2个chunks）
python3 fetch_hsp_batch.py configs/hsp_config_test.yaml \
  --date-from "2024-10-01" \
  --date-to "2024-10-14" \
  --phase "TEST"
```

### 测试多个路由

编辑 `configs/hsp_config_test.yaml`，添加更多路由：

```yaml
routes:
  - name: "EUS-MAN"
    description: "London Euston - Manchester Piccadilly"
    from_loc: "EUS"
    to_loc: "MAN"
    from_time: "0700"
    to_time: "0900"
  
  - name: "KGX-EDR"
    description: "London King's Cross - Edinburgh"
    from_loc: "KGX"
    to_loc: "EDR"
    from_time: "0700"
    to_time: "0900"
```

## 监控和调试

### 查看实时日志

```bash
# 方法1: 使用tail -f
tail -f logs/test_batch_*.log

# 方法2: 查看所有日志文件
ls -lt logs/test_batch_*.log | head -5
```

### 检查数据库

```bash
# 查看测试数据库
sqlite3 data/railfair_test.db "SELECT COUNT(*) FROM hsp_service_metrics;"
sqlite3 data/railfair_test.db "SELECT * FROM hsp_service_metrics LIMIT 5;"
```

### 检查进度文件

```bash
# 查看进度
cat data/progress_test.json | python3 -m json.tool
```

## 预期行为

### 正常运行时应该看到：

1. **日期拆分信息**:
   ```
   📅 Date range split into 1 chunks (≤7 days each)
   ```

2. **请求间隔**:
   ```
   🔍 Chunk 1/1: WEEKDAY (2024-10-01 to 2024-10-07)
   Rate limiting: sleeping for 3.45s
   ```

3. **数据收集**:
   ```
   ✅ Found 15 services
   📊 Progress: 10 records saved
   ```

4. **完成信息**:
   ```
   ✅ Route EUS-MAN completed: 15 records saved
   ```

## 常见问题

### Q: 进程启动失败？
A: 检查：
- `.env` 文件是否存在且包含 `HSP_EMAIL`/`HSP_USERNAME` 和 `HSP_PASSWORD`
- 配置文件路径是否正确
- Python 环境是否正确

### Q: 如何查看完整的错误信息？
A: 查看日志文件：
```bash
cat logs/test_batch_*.log
```

### Q: 如何重新运行失败的测试？
A: 删除进度文件后重新运行：
```bash
rm data/progress_test.json
./test_batch_background.sh
```

### Q: 如何测试更长的日期范围？
A: 修改配置文件中的日期，或使用命令行参数：
```bash
python3 fetch_hsp_batch.py configs/hsp_config_test.yaml \
  --date-from "2024-10-01" \
  --date-to "2024-10-31"
```

## 性能预期

基于测试配置（7天，1路由，WEEKDAY，2小时窗口）：
- **预计请求数**: ~1-2个（取决于数据量）
- **预计运行时间**: 5-15分钟（包括3-5秒间隔）
- **预计记录数**: 10-50条（取决于实际服务数量）

## 下一步

测试成功后，可以：
1. 增加日期范围（14天、30天）
2. 添加更多路由
3. 测试 WEEKEND 数据收集
4. 运行完整的 Phase 1 配置

