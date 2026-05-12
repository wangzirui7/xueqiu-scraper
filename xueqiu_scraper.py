import argparse
import asyncio
import json
import os
import sys

from playwright.async_api import async_playwright


async def scrape_xueqiu(user_id: str, state_file: str, max_pages: int = 1):
    state_file_path = os.path.expanduser(state_file)
    if not os.path.exists(state_file_path):
        print(f"Error: State file {state_file_path} not found.", file=sys.stderr)
        print("Please export your browser cookies/state to this JSON file first.", file=sys.stderr)
        return

    async with async_playwright() as p:
        # We use a real Chrome headful mode to pass WAF
        browser = await p.chromium.launch(
            headless=False,
            channel="chrome",  # Require real chrome
        )
        
        # Load state containing cookies
        context = await browser.new_context(storage_state=state_file_path)
        page = await context.new_page()
        
        try:
            print("Navigating to homepage to pass WAF...", file=sys.stderr)
            # WAF-free navigation to root
            await page.goto("https://xueqiu.com/", wait_until="domcontentloaded")
            # Wait a bit to ensure session is initialized and WAF checks complete if any
            await page.wait_for_timeout(2000)
            
            all_posts = []
            
            for page_num in range(1, max_pages + 1):
                print(f"Fetching posts for user {user_id}, page {page_num}...", file=sys.stderr)
                
                # Fetch directly from the browser context to bypass navigation WAF on /u/*
                fetch_code = f"""
                    async () => {{
                        const response = await fetch('/statuses/user_timeline.json?user_id={user_id}&page={page_num}');
                        if (!response.ok) {{
                            throw new Error(`HTTP error! status: ${{response.status}}`);
                        }}
                        return await response.json();
                    }}
                """
                
                try:
                    data = await page.evaluate(fetch_code)
                    
                    if not data or "statuses" not in data:
                        print(f"No more statuses found or invalid response on page {page_num}", file=sys.stderr)
                        break
                        
                    statuses = data["statuses"]
                    if not statuses:
                        print(f"Empty statuses on page {page_num}", file=sys.stderr)
                        break
                        
                    for post in statuses:
                        parsed_post = {
                            "id": post.get("id"),
                            "text": post.get("text"),
                            "created_at": post.get("created_at"),
                            "fav_count": post.get("fav_count", 0),
                            "retweet_count": post.get("retweet_count", 0),
                            "comment_count": post.get("reply_count", 0), # Xueqiu uses reply_count
                        }
                        all_posts.append(parsed_post)
                        
                    # Small delay between pages
                    if page_num < max_pages:
                        await page.wait_for_timeout(1000)
                        
                except Exception as e:
                    print(f"Error fetching page {page_num}: {e}", file=sys.stderr)
                    break
                    
            return all_posts
            
        finally:
            await browser.close()


def main():
    parser = argparse.ArgumentParser(description="Scrape Xueqiu user posts using Playwright WAF bypass.")
    parser.add_argument("--user-id", default="1247347556", help="Xueqiu user ID (default: 1247347556 for 段永平)")
    parser.add_argument("--state-file", default="~/.hermes/xueqiu_state.json", help="Path to Playwright state JSON file")
    parser.add_argument("--pages", type=int, default=1, help="Number of pages to scrape")
    parser.add_argument("--output", help="Output JSON file (default: stdout)")
    
    args = parser.parse_args()
    
    posts = asyncio.run(scrape_xueqiu(args.user_id, args.state_file, args.pages))
    
    if posts:
        json_output = json.dumps(posts, ensure_ascii=False, indent=2)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(json_output)
            print(f"Saved {len(posts)} posts to {args.output}", file=sys.stderr)
        else:
            print(json_output)
    else:
        print("No posts found or scraping failed.", file=sys.stderr)


if __name__ == "__main__":
    main()
