"""
YouTube upload for Peter+Stewie teaching videos.
Uploads all generated family guy dialogue videos, scheduled 1/day.
"""
import os
import sys
import pickle
from datetime import datetime, timedelta, timezone
from pathlib import Path
import googleapiclient.discovery
import googleapiclient.http
from google.auth.transport.requests import Request

CLIENT_SECRETS = "/home/osno/mind/credentials/yt_client_secrets.json"
TOKEN_FILE = "/home/osno/mind/credentials/yt_token.pickle"
OUTPUT_DIR = Path("/home/osno/projects/osno-brainrot/output")

# Video metadata by topic
VIDEOS = [
    {
        "file": "peter_stewie_compound_interest.mp4",
        "title": "Stewie Teaches Peter About Compound Interest 💰 #shorts",
        "description": "Stewie explains compound interest to Peter Griffin. Your money can make money — but only if you start now.\n\n#familyguy #investing #money #shorts #compound_interest",
        "tags": ["family guy", "stewie", "peter griffin", "investing", "compound interest", "money", "shorts", "finance"],
    },
    {
        "file": "peter_stewie_salary_negotiation.mp4",
        "title": "Stewie Teaches Peter How To Negotiate Salary 💼 #shorts",
        "description": "Never name your salary first. Stewie explains the one rule that can get you thousands more.\n\n#familyguy #negotiation #salary #career #shorts",
        "tags": ["family guy", "stewie", "peter griffin", "salary negotiation", "career", "money", "shorts"],
    },
    {
        "file": "peter_stewie_cashback_hack.mp4",
        "title": "Stewie Explains The Cashback Credit Card Hack 💳 #shorts",
        "description": "You're leaving free money on the table every month. Stewie breaks down how cashback cards work.\n\n#familyguy #moneyhack #cashback #creditcard #shorts",
        "tags": ["family guy", "stewie", "peter griffin", "cashback", "credit card", "money hack", "shorts"],
    },
    {
        "file": "peter_stewie_4_percent_rule.mp4",
        "title": "Stewie Teaches Peter The 4% Rule (How To Retire) 🏖️ #shorts",
        "description": "The one number you need to retire. Stewie explains the 4% rule to Peter Griffin.\n\n#familyguy #retirement #4percentrule #investing #fire #shorts",
        "tags": ["family guy", "stewie", "peter griffin", "4 percent rule", "retire", "FIRE", "investing", "shorts"],
    },
    {
        "file": "peter_stewie_keyboard_shortcuts.mp4",
        "title": "Stewie Teaches Peter Keyboard Shortcuts ⌨️ #shorts",
        "description": "Stop wasting hours clicking around. Stewie teaches Peter the keyboard shortcuts everyone should know.\n\n#familyguy #tech #keyboard #shortcuts #productivity #shorts",
        "tags": ["family guy", "stewie", "peter griffin", "keyboard shortcuts", "tech tips", "productivity", "shorts"],
    },
    {
        "file": "peter_stewie_inflation_cash.mp4",
        "title": "Stewie Explains Why Keeping Cash Is Losing You Money 📉 #shorts",
        "description": "That €10k in your savings account? Inflation is eating it alive. Stewie explains.\n\n#familyguy #inflation #money #investing #shorts",
        "tags": ["family guy", "stewie", "peter griffin", "inflation", "money", "savings", "investing", "shorts"],
    },
    {
        "file": "peter_stewie_sleep_debt.mp4",
        "title": "Stewie Teaches Peter Why You Can't Catch Up On Sleep 😴 #shorts",
        "description": "Sleeping in on weekends doesn't fix sleep debt. Stewie explains the science.\n\n#familyguy #sleep #health #productivity #shorts",
        "tags": ["family guy", "stewie", "peter griffin", "sleep", "sleep debt", "health", "shorts"],
    },
]


def get_authenticated_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            from google_auth_oauthlib.flow import InstalledAppFlow
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRETS,
                ["https://www.googleapis.com/auth/youtube.upload"]
            )
            creds = flow.run_local_server(port=0, open_browser=True)
        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)
    return googleapiclient.discovery.build("youtube", "v3", credentials=creds)


def upload_video(youtube, video_path, title, description, tags, scheduled_time):
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": "22",  # People & Blogs
        },
        "status": {
            "privacyStatus": "private",
            "publishAt": scheduled_time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "selfDeclaredMadeForKids": False,
        },
    }
    media = googleapiclient.http.MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        resumable=True,
        chunksize=1024 * 1024,
    )
    req = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        status, response = req.next_chunk()
        if status:
            print(f"  {int(status.progress() * 100)}%", end="\r")
    print(f"  ✅ Uploaded: {response['id']}")
    return response['id']


if __name__ == "__main__":
    # Schedule: start from tomorrow at 17:00 UTC (best time for engagement)
    start_dt = datetime.now(timezone.utc).replace(hour=17, minute=0, second=0, microsecond=0)
    if start_dt < datetime.now(timezone.utc):
        start_dt += timedelta(days=1)

    print("Authenticating...")
    youtube = get_authenticated_service()

    uploaded = []
    failed = []
    schedule_day = 0

    for v in VIDEOS:
        video_path = OUTPUT_DIR / v["file"]
        if not video_path.exists():
            print(f"⚠️  MISSING: {v['file']} — skipping")
            failed.append(v["file"])
            continue

        scheduled = start_dt + timedelta(days=schedule_day)
        print(f"\n[{schedule_day+1}/{len(VIDEOS)}] {v['title'][:50]}")
        print(f"  File: {video_path.name} ({video_path.stat().st_size/1024/1024:.1f}MB)")
        print(f"  Scheduled: {scheduled.strftime('%Y-%m-%d %H:%M UTC')}")

        try:
            vid_id = upload_video(
                youtube, video_path,
                v["title"], v["description"], v["tags"],
                scheduled
            )
            uploaded.append({"file": v["file"], "id": vid_id, "scheduled": str(scheduled)})
            schedule_day += 1
        except Exception as e:
            print(f"  ❌ Failed: {e}")
            failed.append(v["file"])
            if "uploadLimitExceeded" in str(e) or "quotaExceeded" in str(e):
                print("  ⛔ Quota exceeded — stopping. Try again after midnight PT.")
                break

    print(f"\n=== Done: {len(uploaded)} uploaded, {len(failed)} failed ===")
    for u in uploaded:
        print(f"  ✅ {u['file']} → {u['id']} @ {u['scheduled']}")
    for f in failed:
        print(f"  ❌ {f}")
