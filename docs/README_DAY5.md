# Day 5 使用指南 🚆

## 📊 当前数据状态

根据您提供的信息，当前数据库包含：
- **Metrics表**: 1,145 条记录
- **Details表**: 58,394 条记录

这已经超过了 Week 1 的目标（10,000条记录）！

## 🚀 快速开始

### 1. 首先运行快速统计，了解数据现状

```bash
cd ~/uk-rail-delay-predictor
python3 quick_stats.py data/railfair.db
```

这会显示：
- 各表记录数
- 实际覆盖的路线
- TOC分布
- 日期范围
- 延误统计
- 数据完整性

### 2. 运行完整的Day 5验证流程

```bash
# 一键运行所有Day 5任务
python3 run_day5.py
```

或者分步运行：

```bash
# Step 1: 数据验证
python3 validate_data.py --db data/railfair.db \
  --output data/validation_report_day5.txt \
  --json data/validation_results_day5.json

# Step 2: 数据清理（可选，但推荐）
python3 clean_data.py --db data/railfair.db

# Step 3: 加载元数据
python3 collect_metadata.py

# Step 4: 查看结果
cat data/validation_report_day5.txt
cat data/metadata_report.txt
```

## 📁 文件说明

| 文件名 | 用途 | 运行时间 |
|--------|------|----------|
| quick_stats.py | 快速数据统计 | ~1秒 |
| validate_data.py | 完整数据验证（含ORR标准+PPM） | ~5-10秒 |
| collect_metadata.py | 加载TOC/站点元数据 | ~2-3秒 |
| clean_data.py | 数据清理（极端值、时间不一致） | ~3-5秒 |
| run_day5.py | 运行所有Day 5任务 | ~15-20秒 |

## 📈 预期输出

### quick_stats.py 输出示例
```
============================================================
📊 QUICK DATABASE STATISTICS
============================================================

📋 Table Record Counts:
  hsp_service_metrics       : 1,145 records
  hsp_service_details       : 58,394 records
  toc_metadata              : 0 records (将被填充)
  station_metadata          : 0 records (将被填充)

🛤️ Routes with Data:
  EUS-MAN    : 245 services
  KGX-EDR    : 189 services
  MAN-LIV    : 156 services
  ...

⏱️ Delay Statistics:
  Average delay: 4.2 minutes
  On-time rate: 68.5%
```

### validate_data.py 输出
- 生成 `validation_report_day5.txt` - 人类可读的报告
- 生成 `validation_results_day5.json` - 机器可读的详细数据
- 质量评分（0-100分）
- **ORR标准延迟分析**：
  - On Time (≤1 min)
  - Time to 3 (≤3 min)
  - Time to 15, 30, 60
  - 取消服务统计
- **PPM计算**：
  - PPM-5 (≤5 min)
  - PPM-10 (≤10 min)
  - 按TOC和路线分组
- Week 1目标达成情况
- 具体的改进建议

### collect_metadata.py 输出
- 添加20个TOC的详细信息
- 添加24个主要站点信息
- 添加10条路线的元数据
- 添加7条标准补偿规则
- 自动丰富现有数据（添加名称等）

### clean_data.py 输出
- 修复极端延迟值（>180分钟）
- 修复跨午夜时间不一致问题
- 重新计算缺失的延迟值
- 清理无效记录
- 生成清理报告

## 🎯 关键检查点

运行后，请特别注意：

1. **数据量是否达标**
   - ✅ 目标：>10,000条记录
   - 您的数据：58,394条 ✅

2. **路线覆盖情况**
   - 目标：10条路线
   - 已修复路线代码：
     - KGX-EDR → KGX-EDB (Edinburgh)
     - MYB-BHM → EUS-BHM (London Euston → Birmingham)
     - MAN-LDS → MCV-LDS (Manchester Victoria → Leeds)
   - 需要验证实际覆盖数

3. **数据质量分数**
   - 目标：>70分
   - 验证脚本会计算实际分数

4. **关键问题**
   - 是否有严重错误（红色❌标记）
   - 警告数量是否过多（黄色⚠️标记）

## 🐛 常见问题

### Q: 数据库找不到
A: 确保在正确的目录，数据库应该在 `data/railfair.db`

### Q: Python模块缺失
A: 安装依赖：
```bash
pip install sqlite3 json pathlib
```

### Q: 权限错误
A: 确保有写入权限：
```bash
chmod 755 *.py
```

## 📊 下一步（Day 6-7）

基于Day 5的验证结果，Day 6-7将：

1. **创建统计汇总表**
   - route_statistics
   - toc_performance
   - daily_summaries

2. **计算关键指标**
   - 准点率（按路线/TOC/时段）
   - 平均延误时间
   - 延误模式识别

3. **建立缓存机制**
   - 预计算常用查询
   - 创建性能索引
   - 实现快速查询(<50ms)

## 💡 使用建议

1. **先运行quick_stats.py**
   - 快速了解数据现状
   - 确认数据库可访问

2. **再运行完整验证**
   - 获得详细的质量报告
   - 识别具体问题

3. **最后加载元数据**
   - 丰富现有数据
   - 为后续分析做准备

## 📞 需要帮助？

如果遇到问题：
1. 检查错误信息
2. 查看生成的日志文件
3. 确认数据库路径正确
4. 验证Python版本 >= 3.7

---

**准备好了吗？** 让我们开始Day 5的验证工作！ 🚀
