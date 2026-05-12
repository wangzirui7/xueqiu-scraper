#!/usr/bin/env python3
"""
雪球实时监控 — 段永平发帖第一时间转发到 Home Channel
使用 curl 直调 timeline API，无需 Playwright（响应 ~0.38s）

Usage:
    python3 xueqiu_monitor.py --user-id 1247347556 [--dry-run] [--pages 3]
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# --- 配置 ---
STATE_FILE = Path("~/.hermes/xueqiu_state.json").expanduser()
LAST_POST_FILE = Path("~/.hermes/xueqiu_last_post.json").expanduser()
DEFAULT_USER_ID = "1247347556"  # 段永平


def load_cookies() -> str:
    """从 state_file 加载 cookie 字符串"""
    if not STATE_FILE.exists():
        print(f"Cookie 文件不存在: {STATE_FILE}", file=sys.stderr)
        print("请先在浏览器登录雪球后导出 Cookie 到该文件", file=sys.stderr)
        sys.exit(1)

    with open(STATE_FILE) as f:
        cookies = json.load(f)

    return "; ".join([f"{c['name']}={c['value']}" for c in cookies])


def fetch_timeline(user_id: str, pages: int = 3) -> list:
    """
    使用 curl 直调 timeline API，绕过 WAF
    响应时间约 0.38s，无需 Playwright
    """
    cookies = load_cookies()
    all_posts = []

    for page in range(1, pages + 1):
        url = f"https://xueqiu.com/statuses/user_timeline.json?user_id={user_id}&page={page}"

        cmd = [
            "curl", "-s", "--max-time", "10",
            url,
            "-H", f"Cookie: {cookies}",
            "-H", "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "-H", "Accept: application/json, text/plain, */*",
            "-H", "Referer: https://xueqiu.com/",
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if result.returncode != 0:
                print(f"curl failed (page {page}): {result.stderr}", file=sys.stderr)
                break

            data = json.loads(result.stdout)

            if not data or "statuses" not in data:
                break

            statuses = data["statuses"]
            if not statuses:
                break

            all_posts.extend(statuses)

            # 礼貌延迟
            if page < pages:
                time.sleep(0.3)

        except subprocess.TimeoutExpired:
            print(f"请求超时 (page {page})", file=sys.stderr)
            break
        except json.JSONDecodeError:
            print(f"JSON 解析失败 (page {page})，响应: {result.stdout[:200]}", file=sys.stderr)
            break

    return all_posts


def load_last_post() -> dict:
    if LAST_POST_FILE.exists():
        with open(LAST_POST_FILE) as f:
            return json.load(f)
    return {"id": None, "created_at": None}


def save_last_post(post: dict):
    LAST_POST_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LAST_POST_FILE, "w") as f:
        json.dump(post, f, ensure_ascii=False, indent=2)


def detect_new_posts(new_posts: list, last_post_id) -> list:
    """返回比 last_post_id 更新的帖子（按时间倒序）"""
    new = []
    for post in new_posts:
        if str(post.get("id")) == str(last_post_id):
            break
        new.append(post)
    return new


def strip_html(text: str) -> str:
    """去除 HTML 标签"""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'&#\d+;', '', text)
    return text.strip()


def format_post(post: dict) -> str:
    """格式化帖子内容"""
    text = strip_html(post.get("text", ""))

    created_at = post.get("created_at", 0)
    if created_at:
        dt = datetime.fromtimestamp(created_at / 1000)
        time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
    else:
        time_str = "未知时间"

    stats = []
    if post.get("fav_count", 0) > 0:
        stats.append(f"👍 {post['fav_count']}")
    if post.get("retweet_count", 0) > 0:
        stats.append(f"🔄 {post['retweet_count']}")
    if post.get("reply_count", 0) > 0:
        stats.append(f"💬 {post['reply_count']}")

    stats_str = " | ".join(stats)
    post_url = f"https://xueqiu.com/{post.get('user', {}).get('id', user_id)}/{post['id']}"

    return (
        f"【雪球新帖】\n\n{text}\n\n"
        f"⏰ {time_str}\n"
        f"{stats_str}\n\n"
        f"🔗 {post_url}"
    )


def main():
    parser = argparse.ArgumentParser(description="雪球监控 — 新帖第一时间转发")
    parser.add_argument("--user-id", default=DEFAULT_USER_ID, help="雪球用户ID")
    parser.add_argument("--dry-run", action="store_true", help="仅打印，不写通知文件")
    parser.add_argument("--pages", type=int, default=3, help="每次抓取页数（默认3）")
    args = parser.parse_args()

    user_id = args.user_id

    print(
        f"[{datetime.now().strftime('%H:%M:%S')}] 检查雪球用户 {user_id}...",
        file=sys.stderr,
    )

    posts = fetch_timeline(user_id, pages=args.pages)

    if not posts:
        print("未获取到帖子（Cookie 可能已过期或网络问题）", file=sys.stderr)
        sys.exit(1)

    last_post = load_last_post()
    last_id = last_post.get("id")

    new_posts = detect_new_posts(posts, last_id)

    if not new_posts:
        print(f"无新帖（最新: {posts[0]['id']}）", file=sys.stderr)
        sys.exit(0)

    print(f"发现 {len(new_posts)} 篇新帖！", file=sys.stderr)

    # 输出最新帖到 stdout（Hermes Cron 捕获）
    for post in new_posts:
        msg = format_post(post)
        print(msg)  # stdout — Hermes Cron 会捕获

        if not args.dry_run:
            # 写入通知文件，供 Hermes 处理后推送到 Home Channel
            notify_file = f"/tmp/xueqiu_notify_{post['id']}.json"
            with open(notify_file, "w") as f:
                json.dump({"post": post, "message": msg}, f, ensure_ascii=False)
            print(f"通知已写入 {notify_file}", file=sys.stderr)

    # 更新 last_post_id（写入最新一篇的 id）
    save_last_post({"id": posts[0]["id"], "created_at": posts[0].get("created_at")})
    print(f"last_post_id 已更新: {posts[0]['id']}", file=sys.stderr)


if __name__ == "__main__":
    main()
