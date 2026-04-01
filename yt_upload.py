"""
YouTube upload + scheduling via YouTube Data API v3.
Uploads all 10 brainrot shorts as private, scheduled 1/day starting April 2, 2026.

Usage:
    python3 yt_upload.py                    # upload all 10
    python3 yt_upload.py --index 2          # upload only video #2
    python3 yt_upload.py --auth-only        # just do OAuth flow
"""
import json
import os
import sys
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
import googleapiclient.discovery
import googleapiclient.http
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle

# Config
CLIENT_SECRETS = "/home/osno/mind/credentials/yt_client_secrets.json"
TOKEN_FILE = "/home/osno/mind/credentials/yt_token.pickle"
MANIFEST = "/home/osno/projects/osno-brainrot/output/manifest.json"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

# Schedule: video 1 already uploaded manually (skip or overwrite)
# Videos 2-10 start from April 2, 2026 at 14:00 UTC
SCHEDULE_START = datetime(2026, 4, 2, 14, 0, 0, tzinfo=timezone.utc)
SCHEDULE_INTERVAL_DAYS = 1

# Video already uploaded manually
ALREADY_UPLOADED = {1}  # index 1 was uploaded via browser


def get_authenticated_service():
    """Get authenticated YouTube service, handling OAuth flow."""
    creds = None

    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS, SCOPES)
            # Use out-of-band flow (no localhost server needed)
            creds = flow.run_local_server(port=0, open_browser=True)

        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)

    return googleapiclient.discovery.build("youtube", "v3", credentials=creds)


def upload_video(youtube, video_path, title, subreddit, scheduled_time):
    """Upload a single video and schedule it."""
    print(f"\n📤 Uploading: {title[:60]}...")
    print(f"   File: {video_path}")
    print(f"   Scheduled: {scheduled_time.strftime('%Y-%m-%d %H:%M UTC')}")

    # Video metadata
    description = f"Story from r/{subreddit}\n\n#shorts #reddit #aita #story"

    body = {
        "snippet": {
            "title": title[:100],  # YouTube max 100 chars
            "description": description,
            "tags": ["shorts", "reddit", "story", "aita", "tifu", "brainrot"],
            "categoryId": "22",  # People & Blogs
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
        chunksize=10 * 1024 * 1024  # 10MB chunks
    )

    request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=media
    )

    # Upload with progress
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            print(f"   Progress: {pct}%", end="\r")

    video_id = response.get("id")
    print(f"   ✅ Uploaded: https://youtube.com/shorts/{video_id}")
    print(f"   Scheduled for: {scheduled_time.strftime('%Y-%m-%d %H:%M UTC')}")
    return video_id


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--auth-only", action="store_true", help="Only do OAuth, don't upload")
    parser.add_argument("--index", type=int, default=None, help="Upload only this video index (1-10)")
    parser.add_argument("--skip-uploaded", action="store_true", default=True, help="Skip already uploaded videos")
    args = parser.parse_args()

    print("🔑 Authenticating with YouTube...")
    youtube = get_authenticated_service()
    print("✅ Authenticated!")

    if args.auth_only:
        print("Auth-only mode. Done.")
        return

    # Load manifest
    with open(MANIFEST) as f:
        videos = json.load(f)

    # Filter to upload
    to_upload = []
    schedule_offset = 0

    for video in sorted(videos, key=lambda v: v["index"]):
        idx = video["index"]
        if args.index and idx != args.index:
            continue
        if args.skip_uploaded and idx in ALREADY_UPLOADED:
            print(f"⏭  Skipping video {idx} (already uploaded)")
            continue
        if not Path(video["file"]).exists():
            print(f"⚠️  File not found: {video['file']}")
            continue

        file_size = Path(video["file"]).stat().st_size
        if file_size < 1_000_000:  # < 1MB = probably corrupted
            print(f"⚠️  Video {idx} looks corrupted ({file_size} bytes): {video['file']}")
            continue

        scheduled = SCHEDULE_START + timedelta(days=schedule_offset)
        to_upload.append((video, scheduled))
        schedule_offset += 1

    if not to_upload:
        print("Nothing to upload.")
        return

    print(f"\n📋 Plan: {len(to_upload)} videos to upload")
    for video, sched in to_upload:
        print(f"   [{video['index']}] {video['title'][:60]}...")
        print(f"        → {sched.strftime('%Y-%m-%d %H:%M UTC')}")

    print("\nStarting uploads...\n")

    results = []
    for video, scheduled_time in to_upload:
        try:
            video_id = upload_video(
                youtube,
                video["file"],
                video["title"],
                video["subreddit"],
                scheduled_time
            )
            results.append({"index": video["index"], "video_id": video_id, "scheduled": scheduled_time.isoformat()})
        except Exception as e:
            print(f"❌ Error uploading video {video['index']}: {e}")
            results.append({"index": video["index"], "error": str(e)})

    # Save results
    results_file = "/home/osno/projects/osno-brainrot/upload_results.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n✅ Done! Results saved to {results_file}")
    print(f"\nSummary:")
    for r in results:
        if "video_id" in r:
            print(f"  [{r['index']}] ✅ {r['video_id']} → {r['scheduled']}")
        else:
            print(f"  [{r['index']}] ❌ {r['error']}")


if __name__ == "__main__":
    main()
