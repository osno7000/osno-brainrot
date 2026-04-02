"""
Upload batch4 r/tifu videos to YouTube.
6 videos (skipping duplicates and explicit content) → Apr 18-20, 2/dia.

Run manually or add to cron after combined script finishes.
Safe to run multiple times — tracks progress in upload_log_batch4.json.
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
OUTPUT_DIR = Path("/home/osno/projects/osno-brainrot/output/batch4")
LOG_FILE = Path("/home/osno/projects/osno-brainrot/upload_log_batch4.json")

# Batch4: r/tifu — 6 unique stories, skip duplicates + explicit (short4_06, 07, 09, 10)
SCHEDULE = [
    {
        "key": "batch4/short4_01.mp4",
        "file": str(OUTPUT_DIR / "short4_01.mp4"),
        "publish": datetime(2026, 4, 18, 9, 0, 0, tzinfo=timezone.utc),
        "title": "TIFU by singing Total Eclipse of the Heart during sex 😭 #shorts #reddit",
        "description": "Story from r/tifu\n\n#shorts #reddit #tifu #story #embarrassing",
        "tags": ["reddit", "tifu", "shorts", "story", "embarrassing", "funny"],
        "category": "22",
    },
    {
        "key": "batch4/short4_02.mp4",
        "file": str(OUTPUT_DIR / "short4_02.mp4"),
        "publish": datetime(2026, 4, 18, 17, 0, 0, tzinfo=timezone.utc),
        "title": "TIFU by accidentally starting a crow cult in my neighborhood #shorts #reddit",
        "description": "Story from r/tifu\n\n#shorts #reddit #tifu #story #crow #funny",
        "tags": ["reddit", "tifu", "shorts", "story", "crow", "funny", "neighborhood"],
        "category": "22",
    },
    {
        "key": "batch4/short4_03.mp4",
        "file": str(OUTPUT_DIR / "short4_03.mp4"),
        "publish": datetime(2026, 4, 19, 9, 0, 0, tzinfo=timezone.utc),
        "title": "TIFU by going next door at exactly the wrong time #shorts #reddit",
        "description": "Story from r/tifu\n\n#shorts #reddit #tifu #story #awkward",
        "tags": ["reddit", "tifu", "shorts", "story", "awkward", "neighbor"],
        "category": "22",
    },
    {
        "key": "batch4/short4_04.mp4",
        "file": str(OUTPUT_DIR / "short4_04.mp4"),
        "publish": datetime(2026, 4, 19, 17, 0, 0, tzinfo=timezone.utc),
        "title": "TIFU by accidentally poisoning my family with black mold for years #shorts",
        "description": "Story from r/tifu\n\n#shorts #reddit #tifu #story #health",
        "tags": ["reddit", "tifu", "shorts", "story", "health", "mold", "family"],
        "category": "22",
    },
    {
        "key": "batch4/short4_05.mp4",
        "file": str(OUTPUT_DIR / "short4_05.mp4"),
        "publish": datetime(2026, 4, 20, 9, 0, 0, tzinfo=timezone.utc),
        "title": "TIFU by convincing the internet I was Chevy Chase's secret son for 20 years #shorts",
        "description": "Story from r/tifu\n\n#shorts #reddit #tifu #story #chevy #celebrity",
        "tags": ["reddit", "tifu", "shorts", "story", "celebrity", "chevy chase", "internet"],
        "category": "22",
    },
    {
        "key": "batch4/short4_08.mp4",
        "file": str(OUTPUT_DIR / "short4_08.mp4"),
        "publish": datetime(2026, 4, 20, 17, 0, 0, tzinfo=timezone.utc),
        "title": "TIFU by meowing during a makeout session 😭 #shorts #reddit",
        "description": "Story from r/tifu\n\n#shorts #reddit #tifu #story #cringe #funny",
        "tags": ["reddit", "tifu", "shorts", "story", "cringe", "funny", "embarrassing"],
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
