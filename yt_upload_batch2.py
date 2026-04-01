"""
YouTube upload batch2 — 10 shorts scheduled April 11-20, 2026 @ 17:00 UTC.
"""
import json
import os
import pickle
from datetime import datetime, timedelta, timezone
from pathlib import Path

import googleapiclient.discovery
import googleapiclient.http
from google.auth.transport.requests import Request

CLIENT_SECRETS = "/home/osno/mind/credentials/yt_client_secrets.json"
TOKEN_FILE = "/home/osno/mind/credentials/yt_token.pickle"
MANIFEST = "/home/osno/projects/osno-brainrot/output/batch2/manifest.json"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

# Batch 2: April 11-20, 17:00 UTC
SCHEDULE_START = datetime(2026, 4, 11, 17, 0, 0, tzinfo=timezone.utc)


def get_authenticated_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing token...")
            creds.refresh(Request())
            with open(TOKEN_FILE, "wb") as f:
                pickle.dump(creds, f)
        else:
            raise RuntimeError("No valid credentials. Run yt_auth.py first.")

    return googleapiclient.discovery.build("youtube", "v3", credentials=creds)


def upload_video(youtube, video_path, title, subreddit, scheduled_time):
    print(f"\nUploading: {title[:70]}")
    print(f"  File: {video_path} ({Path(video_path).stat().st_size // 1024 // 1024}MB)")
    print(f"  Scheduled: {scheduled_time.strftime('%Y-%m-%d %H:%M UTC')}")

    description = f"Story from r/{subreddit}\n\n#shorts #reddit #aita #story"

    body = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "tags": ["shorts", "reddit", "story", "aita", "tifu", "brainrot"],
            "categoryId": "22",
            "defaultLanguage": "en",
        },
        "status": {
            "privacyStatus": "private",
            "publishAt": scheduled_time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "selfDeclaredMadeForKids": False,
        }
    }

    media = googleapiclient.http.MediaFileUpload(
        video_path,
        mimetype="video/mp4",
        resumable=True,
        chunksize=10 * 1024 * 1024
    )

    request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=media
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            print(f"  Progress: {pct}%", end="\r")

    video_id = response.get("id")
    print(f"  Done: https://youtube.com/shorts/{video_id}")
    return video_id


def main():
    print("Authenticating...")
    youtube = get_authenticated_service()
    print("OK")

    with open(MANIFEST) as f:
        videos = json.load(f)

    videos = sorted(videos, key=lambda v: v["index"])

    print(f"\nPlan: {len(videos)} videos")
    for i, v in enumerate(videos):
        sched = SCHEDULE_START + timedelta(days=i)
        print(f"  [{v['index']}] {v['title'][:60]} → {sched.strftime('%Y-%m-%d %H:%M UTC')}")

    print("\nStarting uploads...\n")

    results = []
    for i, video in enumerate(videos):
        scheduled_time = SCHEDULE_START + timedelta(days=i)
        video_path = video["video_path"]

        if not Path(video_path).exists():
            print(f"File not found: {video_path}")
            results.append({"index": video["index"], "error": "file not found"})
            continue

        file_size = Path(video_path).stat().st_size
        if file_size < 1_000_000:
            print(f"Suspicious size ({file_size}B): {video_path}")
            results.append({"index": video["index"], "error": f"suspicious size {file_size}"})
            continue

        try:
            video_id = upload_video(
                youtube,
                video_path,
                video["title"],
                video["subreddit"],
                scheduled_time
            )
            results.append({
                "index": video["index"],
                "video_id": video_id,
                "scheduled": scheduled_time.isoformat()
            })
        except Exception as e:
            print(f"Error on video {video['index']}: {e}")
            results.append({"index": video["index"], "error": str(e)})

    results_path = "/home/osno/projects/osno-brainrot/upload_results_batch2.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved: {results_path}")
    print("\nSummary:")
    ok = sum(1 for r in results if "video_id" in r)
    err = sum(1 for r in results if "error" in r)
    print(f"  {ok} OK, {err} errors")
    for r in results:
        if "video_id" in r:
            print(f"  [{r['index']}] {r['video_id']} → {r['scheduled'][:10]}")
        else:
            print(f"  [{r['index']}] ERROR: {r['error']}")


if __name__ == "__main__":
    main()
