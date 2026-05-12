# 雪球 Cookie 导出指南

## 方法一：浏览器 DevTools（推荐）

1. 在浏览器登录 https://xueqiu.com
2. 按 F12 打开 DevTools
3. 切到 **Application** 标签
4. 左侧选择 **Cookies** → `https://xueqiu.com`
5. 复制所有 cookie 为 JSON 数组

### 导出格式

```json
[
  {"name": "xq_a_token", "value": "xxx", "domain": ".xueqiu.com", "path": "/", "secure": true, ...},
  {"name": "xq_id_token", "value": "xxx", "domain": ".xueqiu.com", ...},
  ...
]
```

关键 cookie（必须有）：
- `xq_a_token` — 认证 token
- `xq_id_token` — 用户 ID token
- `cookiesu` — 用户会话

6. 保存到 `~/.hermes/xueqiu_state.json`

## 注意事项

- Cookie 有有效期（约 30 天），过期后需要重新导出
- 必须保持登录状态，退出登录会导致 cookie 失效
- 不同设备/浏览器的 cookie 不通用
