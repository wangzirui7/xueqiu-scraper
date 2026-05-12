# xueqiu-scraper

A python tool for scraping user posts from xueqiu.com using Playwright, specially engineered to bypass Alibaba Cloud WAF without getting blocked. 

这是一个专用于抓取雪球（xueqiu.com）用户发帖的爬虫工具，使用 Playwright 构建，采用了绕过阿里云 WAF 防护的特殊请求技巧。

## How it works / 原理设计

Xueqiu protects its user profile pages (`/u/*`) with strict Alibaba Cloud WAF rules. If you navigate directly to a user's page, you are often blocked or presented with slider captchas, even when using Playwright. 

This scraper bypasses the WAF by:
1. Navigating to the homepage `https://xueqiu.com/` first, which has relaxed WAF rules and initializes the session.
2. Injecting a JS `fetch()` call directly into the browser context to query the internal API `/statuses/user_timeline.json`.
3. Because the API request originates from a valid browser context that has already passed the homepage checks, the WAF allows it sequentially. 

雪球的个人主页包含严格的阿里云 WAF 校验，通常直接访问会被验证码拦截。此工具的爬取思路是：在拥有正常 cookie 的前提下，首先访问雪球主页（WAF 放行），随后在真实的浏览器上下文中通过 `page.evaluate()` 发起注入的 `fetch` API 调用。由于请求是在已经建立良好信任且源自页面的 JS 发出的，可以完美绕过针对 `/u/` 路由的直接拦截规则。

## Installation / 安装

```bash
# Install python dependencies
pip install -r requirements.txt

# Install playwright chromium (requires real Chrome installed locally via the `channel="chrome"` flag)
playwright install chromium
```

## Cookie Setup / 准备 Cookies 

You must export your logged-in Xueqiu session cookies as a Playwright state JSON file. 

1. Log in to xueqiu.com in your normal browser.
2. Export your cookies into a JSON file formatted for Playwright. Make sure it contains the `xq_a_token` cookie.
3. Save it to `~/.hermes/xueqiu_state.json` (or pass the path via CLI argument).

*DO NOT share, commit, or hardcode your `xq_a_token` as it grants full access to your account.*

## Usage / 使用方法

The tool exposes a CLI interface.

```bash
# Scrape user 1247347556 (段永平 / 大道无形我有型) - 1 page
python xueqiu_scraper.py --user-id 1247347556 --pages 1

# Scrape and save to file
python xueqiu_scraper.py --user-id 1247347556 --pages 5 --output posts.json

# Use custom state file location
python xueqiu_scraper.py --state-file /path/to/my_cookies.json
```

**Python usage:**
```python
import asyncio
from xueqiu_scraper import scrape_xueqiu

# Returns list of parsed dictionaries
posts = asyncio.run(scrape_xueqiu(
    user_id="1247347556", 
    state_file="~/.hermes/xueqiu_state.json",
    max_pages=2
))
print(posts[0]['text'])
```

## Disclaimer / 免责声明
This tool is for educational purposes only. Maintainers are not responsible for any misuse, account bans, or IP blocks. Please respect xueqiu.com limits and terms of service.
仅供学习和技术交流使用，请勿用于非法用途或恶意高频抓取。使用者自行承担后果。
