# 🔧 修复 403 Forbidden 错误

## 问题分析

从控制台和测试结果看到：
1. **403 Forbidden** 错误
2. **Cloudflare Challenge**：后端返回 Cloudflare 的挑战页面
3. 这说明 Cloudflare 正在阻止来自 Netlify 的请求

## 解决方案

### 方案 1: 配置 Cloudflare 允许 Netlify 请求（推荐）

在 Cloudflare Dashboard 中：

1. **进入你的域名设置** (`railfair.uk`)
2. **Security** > **WAF** > **Custom Rules**
3. **创建规则**允许来自 Netlify 的请求：
   - **Rule name**: Allow Netlify
   - **When incoming requests match**: 
     - Field: `http.request.headers.user_agent`
     - Operator: `contains`
     - Value: `Netlify`
   - **Then**: `Allow`

或者更简单的方式：

1. **Security** > **WAF**
2. **Firewall rules** > **Create rule**
3. 设置：
   - **Expression**: `(http.request.headers.user_agent contains "Netlify")`
   - **Action**: `Allow`

### 方案 2: 临时使用直接调用（绕过代理）

如果 Netlify 代理持续有问题，可以临时使用直接调用：

1. **编辑 `frontend/railfair/config.js`**:
```javascript
const configuredBase = 'https://api.railfair.uk';  // 直接调用后端
```

2. **确保后端 CORS 配置正确**（后端应该已经配置了）

3. **提交并重新部署**

### 方案 3: 在 Cloudflare 中配置 IP 白名单

1. **Security** > **WAF**
2. **Tools** > **IP Access Rules**
3. **添加 Netlify IP 范围**（需要查找 Netlify 的 IP 范围）

## 当前状态

已更新 `netlify.toml` 添加了 `User-Agent` 头，这可能会帮助通过 Cloudflare 的保护。

## 下一步

1. **等待 Netlify 重新部署**（已推送更改）
2. **测试是否解决**
3. **如果仍有问题**，使用方案 2（直接调用）

## 验证

部署后，在浏览器控制台运行：

```javascript
// 测试代理
fetch('/api/health')
  .then(r => r.json())
  .then(data => console.log('✅ Proxy works:', data))
  .catch(err => console.error('❌ Proxy failed:', err));

// 测试直接调用（如果代理失败）
fetch('https://api.railfair.uk/health')
  .then(r => r.json())
  .then(data => console.log('✅ Direct call works:', data))
  .catch(err => console.error('❌ Direct call failed:', err));
```

