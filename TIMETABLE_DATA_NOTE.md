# 📅 时刻表数据说明

## 当前状态

### ✅ 已实现：优先使用未来时刻表数据

API端点 `/api/routes/{origin}/{destination}/stops` 现在：

1. **优先使用 NRDP Timetable 数据**（未来时刻表）
   - 从 `data/timetable_parsed.json` 读取
   - 这是未来的计划时刻表，不是历史数据
   - 数据来源：NRDP Timetable 文件

2. **回退到历史数据**（如果时刻表数据不可用）
   - 使用 `hsp_service_details` 表
   - 标记为历史数据，并添加警告提示

## ⚠️ 已知问题

### Timetable 数据中缺少中间站台详情

当前 `data/timetable_parsed.json` 文件：
- ✅ 包含服务的基本信息（起点、终点、时间）
- ❌ **不包含中间站台的详细数据**（`intermediate_stops` 数组为空）

**原因**：
- 在解析和保存timetable数据时，中间站台数据可能没有被包含
- 或者数据格式转换时丢失了

## 🔧 解决方案

### 选项 1: 重新解析 Timetable 数据（推荐）

确保中间站台数据被正确保存：

```bash
# 重新解析timetable文件，确保包含中间站台
python3 analyze_nrdp_timetable.py --include-stops
```

### 选项 2: 实时解析 Timetable 文件

修改API，直接从原始timetable文件实时解析（较慢但完整）：

```python
# 在API中直接解析CIF文件
from analyze_nrdp_timetable import extract_service_times
```

### 选项 3: 使用 HSP API 查询未来服务（最佳）

对于用户查询的未来日期，实时从HSP API获取服务详情：

```python
# 使用HSP API查询未来某天的服务详情
# 这需要HSP API凭据
```

## 📝 当前行为

1. **如果timetable数据存在且匹配路线**：
   - 返回起点和终点站
   - 如果中间站台数据可用，也会返回
   - 标记为 `data_source: "nrdp_timetable"`

2. **如果timetable数据不可用**：
   - 回退到历史HSP数据
   - 标记为 `data_source: "hsp_historical"`
   - 添加警告提示

3. **如果都没有**：
   - 返回空数组
   - 提示需要更新timetable数据

## 🎯 建议

为了获得最佳体验，建议：

1. **重新解析timetable数据**，确保包含中间站台
2. **或者**实现实时HSP API查询（需要API凭据）
3. **或者**定期更新timetable数据，确保包含完整信息

## 📊 数据优先级

```
未来时刻表 (NRDP Timetable)
    ↓ (如果不可用)
历史数据 (HSP Service Details) - 带警告
    ↓ (如果不可用)
空结果 - 提示更新数据
```

