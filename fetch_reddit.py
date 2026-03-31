"""
Fetch engaging Reddit posts for brainrot content.
Uses public Reddit JSON API (no auth needed for basic fetching).
"""
import json
import urllib.request
import urllib.parse
import random
import re
from pathlib import Path


SUBREDDITS = [
    "tifu",
    "AmItheAsshole",
    "maliciouscompliance",
    "TrueOffMyChest",
    "confessions",
    "pettyrevenge",
]

HEADERS = {
    "User-Agent": "osno-brainrot/1.0 (reddit content aggregator)"
}

# Max post body length for a ~60s short
MAX_CHARS = 800
MIN_CHARS = 200


def fetch_top_posts(subreddit: str, limit: int = 10, time_filter: str = "week") -> list:
    """Fetch top posts from a subreddit using public JSON API."""
    url = f"https://www.reddit.com/r/{subreddit}/top.json?limit={limit}&t={time_filter}"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read())
    posts = []
    for item in data["data"]["children"]:
        p = item["data"]
        if p.get("stickied") or p.get("is_video") or not p.get("selftext"):
            continue
        if p["selftext"] in ("[removed]", "[deleted]", ""):
            continue
        body = p["selftext"].strip()
        if len(body) < MIN_CHARS:
            continue
        posts.append({
            "id": p["id"],
            "title": p["title"],
            "body": body,
            "score": p["score"],
            "url": f"https://reddit.com{p['permalink']}",
            "subreddit": subreddit,
            "num_comments": p["num_comments"],
        })
    return posts


def pick_post(subreddits: list = None, max_chars: int = MAX_CHARS) -> dict:
    """Pick a random engaging post, truncated to fit a short."""
    if subreddits is None:
        subreddits = SUBREDDITS

    all_posts = []
    for sub in subreddits:
        try:
            posts = fetch_top_posts(sub)
            all_posts.extend(posts)
            print(f"  r/{sub}: {len(posts)} posts")
        except Exception as e:
            print(f"  r/{sub}: error - {e}")

    if not all_posts:
        raise ValueError("No posts fetched")

    # Sort by score, pick from top 20
    all_posts.sort(key=lambda x: x["score"], reverse=True)
    candidates = all_posts[:20]
    post = random.choice(candidates)

    # Truncate body to fit
    body = post["body"]
    if len(body) > max_chars:
        # Try to cut at sentence boundary
        truncated = body[:max_chars]
        last_period = max(truncated.rfind('. '), truncated.rfind('! '), truncated.rfind('? '))
        if last_period > max_chars * 0.6:
            body = body[:last_period + 1]
        else:
            body = truncated + "..."

    post["body_truncated"] = body
    return post


def build_script(post: dict) -> str:
    """Build the TTS script from a Reddit post."""
    title = post["title"]
    body = post["body_truncated"]
    sub = post["subreddit"]

    # Format for reading
    script = f"{title}. ... {body}"
    return script


if __name__ == "__main__":
    print("Fetching posts...")
    post = pick_post()
    print(f"\nSelected: r/{post['subreddit']} — {post['title'][:60]}...")
    print(f"Score: {post['score']} | Comments: {post['num_comments']}")
    print(f"Body length: {len(post['body_truncated'])} chars")
    script = build_script(post)
    print(f"\nScript preview:\n{script[:300]}...")
