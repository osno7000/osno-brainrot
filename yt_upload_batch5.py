"""
Upload batch5 r/pettyrevenge videos to YouTube.
7 unique videos (skipping duplicates: 06=02=09, 07=03) → Apr 21-24, 2/day except last.

Run manually or add to cron after batch4 finishes.
Safe to run multiple times — tracks progress in upload_log_batch5.json.
"""
import json
import os
import pickle
from datetime import datetime, timezone
from pathlib import Path

import googleapiclient.discovery
import googleapiclient.http
from google.auth.transport.requests import Request

CLIENT_SECRETS = "/home/osno/mind/credentials/yt_client_secrets.json"
TOKEN_FILE = "/home/osno/mind/credentials/yt_token.pickle"
OUTPUT_DIR = Path("/home/osno/projects/osno-brainrot/output/batch5")
LOG_FILE = Path("/home/osno/projects/osno-brainrot/upload_log_batch5.json")

# Batch5: r/pettyrevenge — 7 unique stories, skip duplicates (short5_06=02=09, short5_07=03)
SCHEDULE = [
    {
        "key": "batch5/short5_01.mp4",
        "file": str(OUTPUT_DIR / "short5_01.mp4"),
        "publish": datetime(2026, 4, 21, 9, 0, 0, tzinfo=timezone.utc),
        "title": "TIFU by getting petty revenge on my HOA and it worked TOO well 😭 #shorts #reddit",
        "description": "Story from r/pettyrevenge\n\n#shorts #reddit #pettyrevenge #story #funny",
        "tags": ["reddit", "pettyrevenge", "shorts", "story", "funny", "revenge"],
        "category": "22",
    },
    {
        "key": "batch5/short5_02.mp4",
        "file": str(OUTPUT_DIR / "short5_02.mp4"),
        "publish": datetime(2026, 4, 21, 17, 0, 0, tzinfo=timezone.utc),
        "title": "Petty revenge on my neighbor who stole my parking spot for 6 months 🅿️ #shorts #reddit",
        "description": "Story from r/pettyrevenge\n\n#shorts #reddit #pettyrevenge #story #neighbor",
        "tags": ["reddit", "pettyrevenge", "shorts", "story", "neighbor", "parking", "revenge"],
        "category": "22",
    },
    {
        "key": "batch5/short5_03.mp4",
        "file": str(OUTPUT_DIR / "short5_03.mp4"),
        "publish": datetime(2026, 4, 22, 9, 0, 0, tzinfo=timezone.utc),
        "title": "How I got revenge on a coworker who took credit for my work for 2 years 💼 #shorts #reddit",
        "description": "Story from r/pettyrevenge\n\n#shorts #reddit #pettyrevenge #story #work #revenge",
        "tags": ["reddit", "pettyrevenge", "shorts", "story", "work", "coworker", "revenge"],
        "category": "22",
    },
    {
        "key": "batch5/short5_04.mp4",
        "file": str(OUTPUT_DIR / "short5_04.mp4"),
        "publish": datetime(2026, 4, 22, 17, 0, 0, tzinfo=timezone.utc),
        "title": "My landlord tried to keep my deposit so I left him a special surprise 🐾 #shorts #reddit",
        "description": "Story from r/pettyrevenge\n\n#shorts #reddit #pettyrevenge #story #landlord #funny",
        "tags": ["reddit", "pettyrevenge", "shorts", "story", "landlord", "deposit", "revenge"],
        "category": "22",
    },
    {
        "key": "batch5/short5_05.mp4",
        "file": str(OUTPUT_DIR / "short5_05.mp4"),
        "publish": datetime(2026, 4, 23, 9, 0, 0, tzinfo=timezone.utc),
        "title": "Customer was rude to me daily for a year. I finally had enough 💀 #shorts #reddit",
        "description": "Story from r/pettyrevenge\n\n#shorts #reddit #pettyrevenge #story #customer #service",
        "tags": ["reddit", "pettyrevenge", "shorts", "story", "customer", "service", "revenge"],
        "category": "22",
    },
    {
        "key": "batch5/short5_08.mp4",
        "file": str(OUTPUT_DIR / "short5_08.mp4"),
        "publish": datetime(2026, 4, 23, 17, 0, 0, tzinfo=timezone.utc),
        "title": "My boss stole my idea so I made sure everyone found out 😈 #shorts #reddit",
        "description": "Story from r/pettyrevenge\n\n#shorts #reddit #pettyrevenge #story #boss #work",
        "tags": ["reddit", "pettyrevenge", "shorts", "story", "boss", "work", "revenge"],
        "category": "22",
    },
    {
        "key": "batch5/short5_10.mp4",
        "file": str(OUTPUT_DIR / "short5_10.mp4"),
        "publish": datetime(2026, 4, 24, 9, 0, 0, tzinfo=timezone.utc),
        "title": "My ex tried to ruin my life so I let karma do the work instead 🔥 #shorts #reddit",
        "description": "Story from r/pettyrevenge\n\n#shorts #reddit #pettyrevenge #story #ex #karma",
        "tags": ["reddit", "pettyrevenge", "shorts", "story", "ex", "karma", "revenge"],
        "category": "22",
    },
]


def load_log():
    if LOG_FILE.exists():
        with open(LOG_FILE) as f:
            return json.load(f)
    return {}


def save_log(log):
    with open(LOG_FILE, "w") as f:
        json.dump(log, f, indent=2)


def get_authenticated_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_FILE, "wb") as f:
                pickle.dump(creds, f)
        else:
            raise RuntimeError("No valid credentials. Run yt_auth.py first.")
    return googleapiclient.discovery.build("youtube", "v3", credentials=creds)


def upload_video(youtube, v):
    body = {
        "snippet": {
            "title": v["title"],
            "description": v["description"],
            "tags": v["tags"],
            "categoryId": v["category"],
        },
        "status": {
            "privacyStatus": "private",
            "publishAt": v["publish"].strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "selfDeclaredMadeForKids": False,
        },
    }
    media = googleapiclient.http.MediaFileUpload(
        v["file"], mimetype="video/mp4", resumable=True, chunksize=1024 * 1024
    )
    req = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        status, response = req.next_chunk()
        if status:
            print(f"  {int(status.progress() * 100)}%", end="\r")
    print(f"  ✅ {response['id']}")
    return response["id"]


if __name__ == "__main__":
    log = load_log()
    youtube = get_authenticated_service()

    uploaded, failed, skipped = [], [], []

    for v in SCHEDULE:
        key = v["key"]
        if key in log:
            print(f"⏭️  {key} → already uploaded ({log[key]['id']})")
            skipped.append(key)
            continue

        path = Path(v["file"])
        if not path.exists():
            print(f"⚠️  MISSING: {key}")
            failed.append(key)
            continue

        print(f"\n📤 {v['title'][:65]}")
        print(f"   {path.stat().st_size / 1024 / 1024:.1f}MB  →  {v['publish'].strftime('%b %d %H:%M UTC')}")

        try:
            vid_id = upload_video(youtube, v)
            log[key] = {"id": vid_id, "publish": str(v["publish"]), "title": v["title"]}
            save_log(log)
            uploaded.append(key)
        except Exception as e:
            print(f"  ❌ {e}")
            failed.append(key)
            if "uploadLimitExceeded" in str(e) or "quotaExceeded" in str(e):
                print("\n⛔ Quota exceeded — run again after 09:00 Lisbon")
                break

    total_done = len(log)
    total = len(SCHEDULE)
    print(f"\n{'='*60}")
    print(f"This run:  {len(uploaded)} uploaded | {len(skipped)} skipped | {len(failed)} failed")
    print(f"Overall:   {total_done}/{total} complete")
    if total_done < total:
        print(f"⏳ {total - total_done} pending — run again after quota resets (09:00 Lisbon)")
    else:
        print("🎉 All done!")
