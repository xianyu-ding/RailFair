# 🔍 Netlify 部署问题调试指南

## 问题：Search failed. Please ensure the backend is running.

### 可能的原因

1. **Netlify 代理配置问题**
2. **后端 API 路径不匹配**
3. **CORS 问题**
4. **后端服务未正常运行**

---

## 🔧 调试步骤

### 1. 检查后端是否正常运行

```bash
# 测试健康检查
curl https://api.railfair.uk/health

# 测试预测 API
curl -X POST https://api.railfair.uk/api/predict \
  -H "Content-Type: application/json" \
  -d '{
    "origin": "KGX",
    "destination": "MAN",
    "departure_date": "2024-12-25",
    "departure_time": "09:30",
    "include_fares": true
  }'
```

### 2. 检查 Netlify 代理配置

在浏览器中打开开发者工具（F12），查看 Network 标签页：

1. **执行一次查询**
2. **查看请求详情**：
   - Request URL: 应该是 `https://your-site.netlify.app/api/predict`
   - Status Code: 查看状态码
   - Response: 查看响应内容

### 3. 检查 Netlify 部署日志

在 Netlify Dashboard：
1. 进入你的站点
2. 点击 **Deploys** 标签
3. 查看最新的部署日志
4. 检查是否有错误信息

### 4. 测试 Netlify 代理

在浏览器控制台运行：

```javascript
// 测试代理是否工作
fetch('/api/health')
  .then(r => r.json())
  .then(data => console.log('Proxy test:', data))
  .catch(err => console.error('Proxy error:', err));
```

---

## 🛠️ 常见问题修复

### 问题 1: Netlify 代理返回 404

**原因**: 代理路径配置错误

**修复**: 检查 `netlify.toml` 中的 `to` 路径是否正确

```toml
# 正确配置
from = "/api/*"
to = "https://api.railfair.uk/api/:splat"  # :splat 会匹配 * 部分
```

### 问题 2: CORS 错误

**原因**: 后端没有设置正确的 CORS 头

**修复**: 确保后端设置了 CORS 头，或使用 Netlify 代理（推荐）

### 问题 3: 后端路径不匹配

**原因**: 后端 API 路径与前端请求路径不一致

**检查**:
- 前端请求：`/api/predict`
- 后端端点：`/api/predict` ✓ 应该匹配

### 问题 4: Netlify 代理未生效

**原因**: 需要重新部署

**修复**:
1. 确保 `netlify.toml` 在 `frontend/railfair/` 目录下
2. 提交并推送更改
3. 等待 Netlify 重新部署

---

## 📝 检查清单

- [ ] 后端 `https://api.railfair.uk/health` 返回 200
- [ ] 后端 `https://api.railfair.uk/api/predict` 可以正常调用
- [ ] `netlify.toml` 在 `frontend/railfair/` 目录下
- [ ] `netlify.toml` 中的后端地址正确
- [ ] Netlify 部署成功（无错误）
- [ ] 浏览器控制台没有 CORS 错误
- [ ] Network 标签页显示请求状态码

---

## 🔄 如果问题仍然存在

1. **查看浏览器控制台**：检查具体的错误信息
2. **查看 Network 标签页**：查看请求和响应的详细信息
3. **检查 Netlify 函数日志**：如果有使用 Netlify Functions
4. **联系支持**：提供详细的错误信息和日志

---

## 💡 临时解决方案

如果 Netlify 代理有问题，可以临时使用直接调用：

1. 编辑 `frontend/railfair/config.js`：
```javascript
const configuredBase = 'https://api.railfair.uk';
```

2. 确保后端设置了 CORS 头允许你的 Netlify 域名

3. 提交并重新部署

