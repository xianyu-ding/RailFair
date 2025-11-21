# Phase 2 配置说明

## 请求间隔优化

### Phase 1 vs Phase 2

| 配置项 | Phase 1 | Phase 2 | 说明 |
|--------|---------|---------|------|
| 请求间隔 | 3-5秒 | 2-3秒 | Phase 2 更快 |
| 超时时间 | 180秒 | 180秒 | 相同 |
| 日期块大小 | ≤7天 | ≤7天 | 相同 |
| 其他逻辑 | 相同 | 相同 | 完全相同 |

### 为什么 Phase 2 可以更快？

1. **数据更新**: Phase 2 收集的是最近数据（2025-09-01 到 2025-10-31），API 响应可能更快
2. **风险较低**: 如果遇到限速，可以随时调整回 3-5 秒
3. **测试验证**: Phase 1 已经验证了 3-5 秒的稳定性，Phase 2 可以稍微激进一点

### 配置位置

**Phase 2 配置文件**: `configs/hsp_config_phase2.yaml`

```yaml
api:
  request_interval:
    min: 2.0  # 最小 2 秒
    max: 3.0  # 最大 3 秒
```

**Phase 1 配置文件**: `configs/hsp_config_phase1.yaml`

```yaml
api:
  request_interval:
    min: 3.0  # 最小 3 秒
    max: 5.0  # 最大 5 秒
```

## 性能对比

### Phase 1 (3-5秒间隔)
- 270 任务 × 7秒 = ~1,890秒 = ~31分钟（最小）
- 实际: 2-4小时

### Phase 2 (2-3秒间隔)
- 270 任务 × 4秒 = ~1,080秒 = ~18分钟（最小）
- 预计: 1.5-2.5小时
- **节省时间**: ~30-40%

## 使用

### 启动 Phase 2
```bash
./run_phase2_background.sh
```

### 监控
```bash
./check_phase2.sh  # 需要创建
# 或
tail -f logs/phase2_batch_*.log
```

### 如果遇到限速

如果 Phase 2 运行时遇到限速错误，可以：

1. **临时调整**: 编辑 `configs/hsp_config_phase2.yaml`，将间隔改回 3-5 秒
2. **停止并重启**: 
   ```bash
   ./stop_phase2.sh
   # 修改配置后
   ./run_phase2_background.sh
   ```

## 注意事项

⚠️ **如果遇到限速**:
- 观察日志中的错误信息
- 如果频繁出现 429 (Too Many Requests) 错误，增加间隔
- 建议先测试运行几个任务，确认 2-3 秒间隔稳定后再全量运行

✅ **优势**:
- 更快完成数据收集
- 其他逻辑完全相同，风险可控
- 可以随时调整回保守设置

