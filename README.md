# xueqiu-scraper

雪球（xueqiu.com）帖子监控工具，支持段永平等用户的新帖第一时间检测与推送。

**核心结论：雪球桌面版没有 WebSocket/SSE 实时推送通道，采用 HTTP 轮询方案。**

---

## 架构

```
┌─────────────────────────────────────────────────────────────┐
│                    雪球监控架构                              │
│                                                             │
│  ~/.hermes/xueqiu_state.json  (17个有效Cookie)              │
│           │                                                │
│           ▼                                                │
│  xueqiu_monitor.py  (curl HTTP轮询 timeline API)            │
│           │                                                │
│           ▼                                                │
│  ~/.hermes/xueqiu_last_post.json  (last_post_id 增量判断)   │
│           │                                                │
│           ▼                                                │
│  Hermes Cron Job (每15分钟触发)  ──→  Home Channel (微信)   │
└─────────────────────────────────────────────────────────────┘

关键发现（逆向分析结果）：
- 雪球桌面版使用 HTTP 短轮询，无 WebSocket/SSE
- /statuses/user_timeline.json API 直调响应 0.38s，无需 Playwright
- taichi-engine/consequence 是阿里云推送（通知计数，非帖子内容）
- 关注用户后雪球不推送发帖通知
```

---

## 文件说明

| 文件 | 用途 |
|------|------|
| `xueqiu_monitor.py` | **生产用监控脚本**，curl 直调 timeline API，Hermes Cron 调用 |
| `xueqiu_scraper.py` | 旧版 Playwright WAF bypass 方案（参考） |
| `requirements.txt` | Python 依赖 |
| `cookies_setup.md` | Cookie 导出说明 |

---

## 快速开始

### 1. 安装依赖

```bash
pip install requests
```

### 2. 导出雪球 Cookie

在浏览器登录 xueqiu.com 后，打开 DevTools → Application → Cookies → 复制全部 cookie 为 JSON 格式，保存到 `~/.hermes/xueqiu_state.json`。

格式：
```json
[
  {"name": "xq_a_token", "value": "xxx", "domain": ".xueqiu.com", ...},
  ...
]
```

### 3. 测试监控

```bash
# 试运行（不发送通知）
python3 xueqiu_monitor.py --dry-run

# 正常运行
python3 xueqiu_monitor.py
```

### 4. 配置 Cron 定时任务

在 Hermes Agent 中：
```
/cron add "雪球段永平发帖监控" --every 15min \\
  --script xueqiu_monitor.py \\
  --notify
```

---

## API 端点

**用户时间线：**
```
GET https://xueqiu.com/statuses/user_timeline.json?user_id=1247347556&page=1
```

段永平用户 ID：`1247347556`

响应时间：约 0.38 秒（无需 Playwright，curl + cookie 直接调）

---

## 雪球逆向分析笔记

### 实时机制分析结论

| 方式 | 结果 |
|------|------|
| WebSocket 连接 | ❌ 零连接 |
| SSE | ❌ 不存在 |
| taichi-engine AMDP 长轮询 | ❌ 仅通知计数，非帖子内容 |
| 关注后推送 | ❌ 不支持 |
| **HTTP 轮询 timeline API** | ✅ 唯一可行方案 |

### 关键端点

- `https://xueqiu.com/service/v3/notifications` — 全局通知计数（1天未读等）
- `https://xueqiu.com/statuses/user_timeline.json` — 用户帖子时间线
- `https://open.xueqiu.com/mpaas/taichi-engine/consequence` — 阿里云推送（Mobile Push）

---

## License

MIT
