# NRDP 真实票价数据配置指南

## 📋 当前状态

### ✅ 已完全实现
- ✅ **完整的NRDP客户端** - `price_fetcher.py` 包含完整的 `NRDPClient` 类
- ✅ **完整的解析器** - `FaresParser` 类可以解析NRDP数据文件
- ✅ **自动数据更新** - 系统每天自动检查并更新数据
- ✅ **仅使用真实数据** - 完全移除模拟数据，只使用NRDP真实数据

### ✅ 必需配置
- `.env` 文件中必须配置：
  - `NRDP_EMAIL=your_email@example.com`
  - `NRDP_PASSWORD=your_password`
- 如果没有配置，系统会抛出错误（不降级到模拟数据）

## 🔧 NRDP API 说明

根据官方文档，NRDP API 需要：

### 1. 认证流程
```bash
POST https://opendata.nationalrail.co.uk/authenticate
Content-Type: application/json

{
  "username": "your_email@example.com",
  "password": "your_password"
}
```

响应：
```json
{
  "token": "user@email.com:1491312310772:56c56baa3e56d35ff0ede4a6aad1bcfb"
}
```

### 2. 下载票价数据
```bash
GET https://opendata.nationalrail.co.uk/api/staticfeeds/2.0/fares
X-Auth-Token: user@email.com:1491312310772:56c56baa3e56d35ff0ede4a6aad1bcfb
```

响应：
- 返回 ZIP 文件
- 包含固定格式的文本文件（.FFL, .NFO, .NDF等）
- 需要解析这些文件

### 3. 数据特点
- **静态数据**：不是实时API，而是定期更新的数据文件
- **更新频率**：NRDP每周更新一次，**系统每天检查一次**
- **文件格式**：固定格式文本文件（RSPS5045规范）
- **数据量**：非常大（500,000+条票价记录）
- **数据标记**：所有数据标记为 `NRDP_REAL`

## ✅ 系统实现

### 已实现的功能

1. **NRDPClient 类** ✅
   - `authenticate()` - 获取认证token
   - `download_fares_data()` - 下载ZIP文件
   - Token管理（自动刷新）

2. **FaresParser 类** ✅
   - 解析ZIP文件
   - 解析固定格式文件（.FFL, .NFO, .NDF）
   - CRS到NLC代码转换
   - 数据验证和过滤

3. **自动数据更新** ✅
   - 系统启动时自动检查数据是否需要更新
   - **每天更新一次** - 如果数据超过1天，自动下载新数据
   - 如果数据未超过1天，使用现有缓存

4. **仅真实数据** ✅
   - 完全移除模拟数据
   - 只返回 `NRDP_REAL` 数据源的数据
   - 如果没有真实数据，返回 `None`，前端显示"不可用"

## 🔍 验证配置

检查你的 `.env` 配置：

```bash
# 检查NRDP配置
grep -E "NRDP" .env
```

应该看到：
```
NRDP_EMAIL=your_email@example.com
NRDP_PASSWORD=your_password_here
```

## 📝 重要注意事项

1. **NRDP API 使用限制**
   - 账户30天不使用会被删除
   - ✅ **系统每天自动检查一次** - 符合最佳实践
   - 不要手动频繁下载数据

2. **数据文件大小**
   - Fares ZIP文件可能很大（几十MB）
   - 解析后数据库可能达到几百MB
   - 需要足够的存储空间

3. **数据真实性保证**
   - ✅ **完全移除模拟数据** - 系统只使用真实NRDP数据
   - ✅ 如果没有真实数据，API返回 `fares: null`
   - ✅ 前端应显示"❌ 不可用（暂无真实票价数据）"
   - ❌ **不降级到模拟数据** - 确保数据真实性

4. **必需配置**
   - ❌ 如果没有NRDP凭据，系统会抛出错误
   - ✅ 必须在 `.env` 文件中配置 `NRDP_EMAIL` 和 `NRDP_PASSWORD`
   - ✅ 系统不会降级到模拟数据

## 🚀 使用方法

### 1. 配置NRDP凭据

在项目根目录的 `.env` 文件中添加：

```bash
NRDP_EMAIL=your_email@example.com
NRDP_PASSWORD=your_password
```

### 2. 启动系统

```bash
python api/app.py
```

系统会自动：
- ✅ 检查 `.env` 文件中的NRDP凭据
- ✅ 检查数据是否需要更新（每天一次）
- ✅ 如果需要更新，自动从NRDP API下载数据
- ✅ 解析并存储到数据库
- ✅ 标记所有数据为 `NRDP_REAL`

### 3. 数据更新策略

系统会在以下情况更新数据：
- ✅ ZIP文件不存在
- ✅ ZIP文件超过1天
- ✅ 数据库为空

系统会在以下情况使用现有数据：
- ✅ ZIP文件存在且未超过1天
- ✅ 数据库中有数据

### 4. 验证数据

```bash
# 检查数据源（应该只看到 NRDP_REAL）
sqlite3 data/railfair.db "SELECT DISTINCT data_source FROM fare_cache;"

# 检查数据数量
sqlite3 data/railfair.db "SELECT COUNT(*) FROM fare_cache WHERE data_source='NRDP_REAL';"

# 检查ZIP文件时间
ls -lh data/fares_data.zip
```

## 📚 相关文档

- NRDP官方文档：https://opendata.nationalrail.co.uk/
- Day 9交付总结：`docs/DAY9_DELIVERY_SUMMARY.md`
- 当前数据来源说明：`api/DATA_SOURCES.md`

