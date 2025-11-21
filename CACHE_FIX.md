# 🔧 缓存键修复说明

## 问题描述

用户发现查询不同路线时，返回的票价和时间表都是固定的，不对。

## 根本原因

`@cached` 装饰器在生成缓存键时只使用了 `kwargs`（关键字参数），但以下函数使用位置参数：
- `get_cached_fare(origin, destination, departure_datetime)` 
- `get_cached_timetable(origin, destination)`

这导致缓存键不包含 `origin` 和 `destination` 信息，所有路线共享同一个缓存键，返回相同的结果。

## 修复方案

修改 `api/redis_cache.py` 中的 `@cached` 装饰器：

1. **使用 `inspect.signature`** 获取函数签名
2. **绑定所有参数**（包括位置参数和关键字参数）
3. **生成包含所有参数的缓存键**

现在缓存键会正确包含：
- `origin`
- `destination`  
- `departure_datetime`
- 其他所有参数

## 测试步骤

1. **重启API服务器**（重要！）
   ```bash
   # 停止当前服务器 (Ctrl+C)
   python3 -m api.app
   ```

2. **清空Redis缓存**（已自动完成）
   ```bash
   redis-cli FLUSHDB
   ```

3. **测试不同路线**：
   ```bash
   # 测试 EUS -> MAN
   curl -X POST http://localhost:8000/api/predict \
     -H "Content-Type: application/json" \
     -d '{"origin":"EUS","destination":"MAN","departure_date":"2025-12-25","departure_time":"09:30","include_fares":true}'
   
   # 测试 EUS -> BHM
   curl -X POST http://localhost:8000/api/predict \
     -H "Content-Type: application/json" \
     -d '{"origin":"EUS","destination":"BHM","departure_date":"2025-12-25","departure_time":"09:30","include_fares":true}'
   ```

4. **验证结果**：
   - 不同路线应该返回不同的票价
   - 不同路线应该返回不同的时间表
   - 相同路线的相同查询应该使用缓存（返回相同结果）

## 预期行为

修复后：
- ✅ 不同路线返回不同的票价数据
- ✅ 不同路线返回不同的时间表数据
- ✅ 相同路线的查询会被正确缓存
- ✅ 缓存键包含完整的路线信息

## 注意事项

- 修复后需要**重启API服务器**才能生效
- 建议清空Redis缓存以确保旧缓存不影响测试
- 如果仍有问题，检查数据库是否有对应路线的数据

