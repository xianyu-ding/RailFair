# 🔍 快速问题检查清单

## 问题 1: 票价显示 "Unavailable" 而不是 "-"

### ✅ 已修复
- `formatCurrency()` 函数已改为返回 `-`
- 所有 "unavailable" 文本已改为使用 `-`

### 🔧 如果还是看到 "Unavailable"

**原因**: 浏览器缓存了旧版本的JavaScript

**解决方法**:
1. **硬刷新页面**:
   - Windows/Linux: `Ctrl + F5` 或 `Ctrl + Shift + R`
   - Mac: `Cmd + Shift + R`

2. **清除浏览器缓存**:
   - Chrome: 设置 → 隐私和安全 → 清除浏览数据 → 选择"缓存的图片和文件"
   - 或者使用无痕模式测试

3. **检查文件是否更新**:
   ```bash
   # 检查formatCurrency函数
   grep -A 3 "function formatCurrency" frontend/railfair/script.js
   # 应该显示: return '-';
   ```

## 问题 2: 中间站台按钮点不进去

### ✅ 已修复
- 添加了正确的事件监听器
- 使用 `setTimeout` 确保DOM已准备好
- 添加了错误处理

### 🔧 如果按钮还是不工作

**检查步骤**:

1. **打开浏览器开发者工具** (F12)
2. **查看 Console 标签页**:
   - 是否有JavaScript错误？
   - 是否有 "Failed to find toggle elements" 错误？

3. **查看 Network 标签页**:
   - 点击按钮后，是否发送了 `/routes/{origin}/{destination}/stops` 请求？
   - 请求是否成功（状态码200）？
   - 响应内容是什么？

4. **手动测试API**:
   ```bash
   curl http://localhost:8000/api/routes/EUS/MAN/stops
   ```

5. **检查按钮HTML**:
   - 在开发者工具中，找到按钮元素
   - 检查按钮ID是否正确（应该是 `result-{timestamp}-toggle`）
   - 检查是否有 `onclick` 属性（不应该有，应该使用事件监听器）

## 问题 3: 每个查询只有一个结果

### ✅ 已修复
- 改为追加模式（使用 `appendChild` 而不是 `innerHTML`）
- 每次新查询时清空旧结果

### 🔧 如果还是只显示一个结果

**检查**:
1. 是否每次查询都清空了旧结果？
2. 是否想要保留多个查询结果？

**当前行为**:
- ✅ 每次新查询时，清空之前的结果
- ✅ 显示新的查询结果

**如果想保留多个查询结果**:
- 需要修改代码，移除 `resultsList.innerHTML = '';` 这一行

## 🧪 完整测试流程

1. **清除浏览器缓存并硬刷新**
   ```
   Ctrl+F5 (Windows) 或 Cmd+Shift+R (Mac)
   ```

2. **测试票价显示**
   - 查询 EUS → MAN
   - 检查票价：应该显示 `-` 而不是 "Unavailable"

3. **测试中间站台**
   - 点击"查看中间站台"按钮
   - 应该展开显示站台列表
   - 如果失败，查看浏览器控制台错误

4. **测试多个查询**
   - 查询第一个路线
   - 查询第二个路线
   - 应该只显示最新的查询结果

## 🐛 调试技巧

### 在浏览器控制台中测试

```javascript
// 测试formatCurrency函数
function formatCurrency(value) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
        return '-';
    }
    return `£${Number(value).toFixed(2)}`;
}

// 测试
console.log(formatCurrency(null));  // 应该输出: "-"
console.log(formatCurrency(42.9)); // 应该输出: "£42.90"
```

### 检查按钮元素

```javascript
// 在浏览器控制台中运行
const buttons = document.querySelectorAll('[id*="-toggle"]');
console.log('找到的按钮:', buttons);
buttons.forEach(btn => {
    console.log('按钮ID:', btn.id);
    console.log('是否有事件监听器:', btn.onclick !== null);
});
```

## 📞 如果问题仍然存在

请提供以下信息：
1. 浏览器类型和版本
2. 浏览器控制台的错误信息（F12 → Console）
3. Network标签页中的请求详情（F12 → Network）
4. 具体的错误现象描述

