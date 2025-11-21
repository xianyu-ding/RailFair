# 数据来源说明

## 📊 当前数据状态

### ✅ Predictor（延误预测）- **使用真实数据**

**数据来源**：
- 从 `data/railfair.db` 数据库的 `route_statistics` 表读取
- 基于 Historical Service Performance (HSP) API 收集的真实历史数据
- 包含真实的延误统计、准点率、历史服务次数等

**证据**：
- 演示显示：`历史数据: 4066 条` - 这是真实的统计数据
- 数据库中有 EUS-MAN 路线的真实统计记录
- 预测结果基于实际的历史性能数据

**数据质量**：
- ✅ 基于 4066+ 个历史服务记录
- ✅ 置信度等级：HIGH（高置信度）
- ✅ 包含真实的平均延误、准点率等统计

### ✅ Price Fetcher（票价比较）- **使用真实NRDP数据**

**当前状态**：
- ✅ **完全使用真实NRDP数据** - 已移除所有模拟数据
- ✅ 从 National Rail Data Portal (NRDP) API 下载真实票价数据
- ✅ 数据标记为 `NRDP_REAL`，存储在 `fare_cache` 表中

**数据更新策略**：
- ✅ **每天自动更新一次** - 检查数据是否超过1天
- ✅ 如果ZIP文件存在且未超过1天，使用现有缓存
- ✅ 如果超过1天或文件不存在，自动从NRDP API下载新数据

**数据特点**：
- ✅ 真实的 National Rail 票价数据
- ✅ 包含 Advance、Off-Peak、Anytime 三种票型
- ✅ 异常价格过滤 (£1-£1000范围)
- ✅ 自动CRS到NLC代码转换

**无数据处理**：
- ✅ 如果没有真实数据，API返回 `fares: null`
- ✅ 前端应显示"❌ 不可用（暂无真实票价数据）"
- ✅ **不降级到模拟数据** - 确保数据真实性

## 🔧 NRDP API 配置

### 必需配置

在 `.env` 文件中必须配置：
```bash
NRDP_EMAIL=your_email@example.com
NRDP_PASSWORD=your_password
```

### 系统行为

- ✅ 如果提供了NRDP凭据，系统会自动下载真实数据
- ❌ 如果没有提供凭据，系统会抛出错误（不降级到模拟数据）
- ✅ 启动时会自动检查数据是否需要更新（每天一次）

## 📈 数据来源总结

| 组件 | 数据来源 | 状态 | 说明 |
|------|---------|------|------|
| **延误预测** | HSP API → 数据库 | ✅ 真实数据 | 基于 4066+ 历史服务记录 |
| **票价比较** | NRDP API → 数据库 | ✅ 真实数据 | 每天自动更新，仅真实数据 |

## 🔍 验证数据真实性

### 检查预测数据

```bash
# 查看数据库中的真实统计数据
sqlite3 data/railfair.db "SELECT origin, destination, total_services, on_time_percentage, avg_delay_minutes FROM route_statistics WHERE origin='EUS' AND destination='MAN' ORDER BY calculation_date DESC LIMIT 1;"
```

### 检查票价数据

```bash
# 查看票价缓存（应该显示 NRDP_REAL）
sqlite3 data/railfair.db "SELECT origin, destination, ticket_type, adult_fare, data_source FROM fare_cache WHERE origin='EUS' AND destination='MAN' AND data_source='NRDP_REAL';"

# 检查数据更新时间
ls -lh data/fares_data.zip
```

### 检查数据更新

```bash
# 查看日志，确认数据更新策略
# 启动服务器时会显示：
# - "✅ 使用现有缓存数据（数据未超过1天）" 或
# - "📊 ZIP文件已存在 X 天（超过 1 天），需要更新"
```

## 💡 重要说明

1. **预测功能**：✅ 已经使用真实数据，可以信任预测结果
2. **票价功能**：✅ **完全使用真实NRDP数据**，不再使用模拟数据
3. **数据更新**：✅ 每天自动检查并更新一次，确保数据新鲜度
4. **无数据处理**：✅ 如果没有真实数据，显示"不可用"，不显示模拟数据

## 📝 配置位置

- **预测数据**：`predictor.py` - 自动从数据库读取真实数据
- **票价数据**：`api/app.py` - 自动从NRDP API下载真实数据
- **NRDP凭据**：`.env` 文件中的 `NRDP_EMAIL` 和 `NRDP_PASSWORD`

