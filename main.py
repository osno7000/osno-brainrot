#!/usr/bin/env python3
"""
osno-brainrot: Reddit brainrot YouTube Shorts generator.

Usage:
  python3 main.py                    # Auto-pick a post and generate
  python3 main.py --test             # Test with hardcoded text
  python3 main.py --subreddit tifu   # Pick from specific subreddit
  python3 main.py --bg path/to/video.mp4  # Use custom background
"""
import argparse
import json
import sys
import time
from pathlib import Path
from datetime import datetime

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

import fetch_reddit
import generate_tts
import assemble_video


OUTPUT_DIR = Path(__file__).parent / "output"
CACHE_DIR = Path(__file__).parent / "cache"
BG_DIR = Path(__file__).parent / "backgrounds"

OUTPUT_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)
BG_DIR.mkdir(exist_ok=True)


def run(
    subreddits=None,
    bg_path=None,
    test_mode=False,
    test_text=None,
):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    job_dir = CACHE_DIR / ts
    job_dir.mkdir()

    print(f"\n{'='*50}")
    print(f"osno-brainrot — {ts}")
    print(f"{'='*50}\n")

    if test_mode:
        print("[TEST MODE]")
        post = {
            "title": "TIFU by putting my laptop in the washing machine",
            "body_truncated": test_text or (
                "So this morning I was running late for work and completely on autopilot. "
                "I grabbed what I thought was my lunchbox from the counter and shoved it "
                "in my bag. Got to work, opened my bag, and there's my MacBook Pro. "
                "Meanwhile, at home, my lunchbox is sitting there safe and sound. "
                "But here's the real kicker — I had already started the washing machine "
                "before I left. It was full of clothes. And my MacBook charger. "
                "Edit: yes the charger is completely destroyed. RIP."
            ),
            "subreddit": "tifu",
            "url": "https://reddit.com/r/tifu/test",
            "score": 99999,
        }
        script = fetch_reddit.build_script(post)
    else:
        print("Step 1: Fetching Reddit post...")
        subs = subreddits or fetch_reddit.SUBREDDITS
        post = fetch_reddit.pick_post(subs)
        script = fetch_reddit.build_script(post)
        print(f"  Selected: r/{post['subreddit']} — {post['title'][:60]}")
        print(f"  Score: {post['score']}")

    # Save post data
    with open(job_dir / "post.json", "w") as f:
        json.dump(post, f, indent=2)

    print(f"\nStep 2: Generating TTS...")
    tts_result = generate_tts.generate(script, str(job_dir))
    duration = tts_result["duration_s"]
    print(f"  Duration: {duration:.1f}s ({len(tts_result['words'])} words)")

    if duration > 90:
        print(f"  Warning: video is {duration:.0f}s, might be too long for Shorts")

    # Find background video
    if not bg_path:
        bg_files = list(BG_DIR.glob("*.mp4")) + list(BG_DIR.glob("*.webm"))
        if bg_files:
            import random
            bg_path = str(random.choice(bg_files))
            print(f"\nStep 3: Using background: {Path(bg_path).name}")
        else:
            print(f"\nStep 3: No background found, using gradient fallback")
            bg_path = None

    print(f"\nStep 4: Assembling video...")
    output_path = OUTPUT_DIR / f"short_{ts}.mp4"

    timing_data = {
        "words": tts_result["words"],
        "duration_s": duration,
    }

    assemble_video.assemble(
        audio_path=tts_result["audio_path"],
        timing_data=timing_data,
        output_path=str(output_path),
        subreddit=post["subreddit"],
        bg_path=bg_path,
    )

    print(f"\n{'='*50}")
    print(f"DONE: {output_path}")
    print(f"Duration: {duration:.1f}s")
    print(f"Post: r/{post['subreddit']} — {post['title'][:50]}")
    print(f"Source: {post['url']}")
    print(f"{'='*50}\n")

    return str(output_path)


def main():
    parser = argparse.ArgumentParser(description="osno-brainrot YouTube Shorts generator")
    parser.add_argument("--test", action="store_true", help="Use test content")
    parser.add_argument("--subreddit", "-s", nargs="+", help="Subreddits to use")
    parser.add_argument("--bg", help="Background video path")
    parser.add_argument("--text", help="Custom text for test mode")
    args = parser.parse_args()

    run(
        subreddits=args.subreddit,
        bg_path=args.bg,
        test_mode=args.test,
        test_text=args.text,
    )


if __name__ == "__main__":
    main()
