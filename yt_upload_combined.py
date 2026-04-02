"""
Combined upload: Family Guy + Reddit, 2 vídeos/dia.

Estado actual (já uploaded):
- Batch1: 7 vídeos agendados Apr 2-8 às 14:00 UTC (os 2 problemáticos foram apagados)

Novos uploads (este script):
- 7 FG videos: Apr 2-8 às 09:00 UTC (par com batch1 existente)
- 9 Batch3 Reddit (skip _01 handjob): Apr 9-13 às 09:00 + 17:00 UTC
- 8 Batch2 Reddit (skip duplicados _04 _07): Apr 13-17

Total: 24 uploads → ~4 dias de quota (6/dia × 1600 units = 10k limit)

Safe to run multiple times — tracks progress in upload_log.json.
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
OUTPUT_DIR = Path("/home/osno/projects/osno-brainrot/output")
LOG_FILE = Path("/home/osno/projects/osno-brainrot/upload_log.json")

SCHEDULE = [
    # ── Family Guy: Apr 2-8 às 09:00 UTC ──────────────────────────────────
    {
        "key": "peter_stewie_compound_interest.mp4",
        "file": str(OUTPUT_DIR / "peter_stewie_compound_interest.mp4"),
        "publish": datetime(2026, 4, 2, 9, 0, 0, tzinfo=timezone.utc),
        "title": "Stewie Teaches Peter About Compound Interest 💰 #shorts",
        "description": "Stewie explains compound interest to Peter Griffin. Your money can make money — but only if you start now.\n\n#familyguy #investing #money #shorts #compound_interest",
        "tags": ["family guy", "stewie", "peter griffin", "investing", "compound interest", "money", "shorts", "finance"],
        "category": "22",
    },
    {
        "key": "peter_stewie_salary_negotiation.mp4",
        "file": str(OUTPUT_DIR / "peter_stewie_salary_negotiation.mp4"),
        "publish": datetime(2026, 4, 3, 9, 0, 0, tzinfo=timezone.utc),
        "title": "Stewie Teaches Peter How To Negotiate Salary 💼 #shorts",
        "description": "Never name your salary first. Stewie explains the one rule that can get you thousands more.\n\n#familyguy #negotiation #salary #career #shorts",
        "tags": ["family guy", "stewie", "peter griffin", "salary negotiation", "career", "money", "shorts"],
        "category": "22",
    },
    {
        "key": "peter_stewie_cashback_hack.mp4",
        "file": str(OUTPUT_DIR / "peter_stewie_cashback_hack.mp4"),
        "publish": datetime(2026, 4, 4, 9, 0, 0, tzinfo=timezone.utc),
        "title": "Stewie Explains The Cashback Credit Card Hack 💳 #shorts",
        "description": "You're leaving free money on the table every month. Stewie breaks down how cashback cards work.\n\n#familyguy #moneyhack #cashback #creditcard #shorts",
        "tags": ["family guy", "stewie", "peter griffin", "cashback", "credit card", "money hack", "shorts"],
        "category": "22",
    },
    {
        "key": "peter_stewie_4_percent_rule.mp4",
        "file": str(OUTPUT_DIR / "peter_stewie_4_percent_rule.mp4"),
        "publish": datetime(2026, 4, 5, 9, 0, 0, tzinfo=timezone.utc),
        "title": "Stewie Teaches Peter The 4% Rule (How To Retire) 🏖️ #shorts",
        "description": "The one number you need to retire. Stewie explains the 4% rule to Peter Griffin.\n\n#familyguy #retirement #4percentrule #investing #fire #shorts",
        "tags": ["family guy", "stewie", "peter griffin", "4 percent rule", "retire", "FIRE", "investing", "shorts"],
        "category": "22",
    },
    {
        "key": "peter_stewie_keyboard_shortcuts.mp4",
        "file": str(OUTPUT_DIR / "peter_stewie_keyboard_shortcuts.mp4"),
        "publish": datetime(2026, 4, 6, 9, 0, 0, tzinfo=timezone.utc),
        "title": "Stewie Teaches Peter Keyboard Shortcuts ⌨️ #shorts",
        "description": "Stop wasting hours clicking around. Stewie teaches Peter the keyboard shortcuts everyone should know.\n\n#familyguy #tech #keyboard #shortcuts #productivity #shorts",
        "tags": ["family guy", "stewie", "peter griffin", "keyboard shortcuts", "tech tips", "productivity", "shorts"],
        "category": "22",
    },
    {
        "key": "peter_stewie_inflation_cash.mp4",
        "file": str(OUTPUT_DIR / "peter_stewie_inflation_cash.mp4"),
        "publish": datetime(2026, 4, 7, 9, 0, 0, tzinfo=timezone.utc),
        "title": "Stewie Explains Why Keeping Cash Is Losing You Money 📉 #shorts",
        "description": "That money in your savings account? Inflation is eating it alive. Stewie explains.\n\n#familyguy #inflation #money #investing #shorts",
        "tags": ["family guy", "stewie", "peter griffin", "inflation", "money", "savings", "investing", "shorts"],
        "category": "22",
    },
    {
        "key": "peter_stewie_sleep_debt.mp4",
        "file": str(OUTPUT_DIR / "peter_stewie_sleep_debt.mp4"),
        "publish": datetime(2026, 4, 8, 9, 0, 0, tzinfo=timezone.utc),
        "title": "Stewie Teaches Peter Why You Can't Catch Up On Sleep 😴 #shorts",
        "description": "Sleeping in on weekends doesn't fix sleep debt. Stewie explains the science.\n\n#familyguy #sleep #health #productivity #shorts",
        "tags": ["family guy", "stewie", "peter griffin", "sleep", "sleep debt", "health", "shorts"],
        "category": "22",
    },
    # ── Batch3 Reddit: Apr 9-13 às 09:00 + 17:00 UTC ──────────────────────
    # (short3_01 handjob TIFU — SKIP, já apagado do YouTube)
    {
        "key": "batch3/short3_02.mp4",
        "file": str(OUTPUT_DIR / "batch3/short3_02.mp4"),
        "publish": datetime(2026, 4, 9, 9, 0, 0, tzinfo=timezone.utc),
        "title": "AITA for not letting others use my office? #shorts #reddit",
        "description": "Story from r/AmItheAsshole\n\n#shorts #reddit #aita #story",
        "tags": ["reddit", "aita", "shorts", "story", "amithejerk"],
        "category": "22",
    },
    {
        "key": "batch3/short3_03.mp4",
        "file": str(OUTPUT_DIR / "batch3/short3_03.mp4"),
        "publish": datetime(2026, 4, 9, 17, 0, 0, tzinfo=timezone.utc),
        "title": "AITA for eating a croissant in a cemetery? #shorts #reddit",
        "description": "Story from r/AmItheAsshole\n\n#shorts #reddit #aita #story",
        "tags": ["reddit", "aita", "shorts", "story", "amithejerk"],
        "category": "22",
    },
    {
        "key": "batch3/short3_04.mp4",
        "file": str(OUTPUT_DIR / "batch3/short3_04.mp4"),
        "publish": datetime(2026, 4, 10, 9, 0, 0, tzinfo=timezone.utc),
        "title": "AITA for refusing to eat my wife's secret spaghetti? #shorts",
        "description": "Story from r/AmItheAsshole\n\n#shorts #reddit #aita #story",
        "tags": ["reddit", "aita", "shorts", "story", "amithejerk"],
        "category": "22",
    },
    {
        "key": "batch3/short3_05.mp4",
        "file": str(OUTPUT_DIR / "batch3/short3_05.mp4"),
        "publish": datetime(2026, 4, 10, 17, 0, 0, tzinfo=timezone.utc),
        "title": "AITAH for moving out after my wife let our kids move home? #shorts",
        "description": "Story from r/AITAH\n\n#shorts #reddit #aitah #story",
        "tags": ["reddit", "aitah", "shorts", "story", "amithejerk"],
        "category": "22",
    },
    {
        "key": "batch3/short3_06.mp4",
        "file": str(OUTPUT_DIR / "batch3/short3_06.mp4"),
        "publish": datetime(2026, 4, 11, 9, 0, 0, tzinfo=timezone.utc),
        "title": "AITAH for sending a kid home from a sleepover at midnight? #shorts",
        "description": "Story from r/AITAH\n\n#shorts #reddit #aitah #story",
        "tags": ["reddit", "aitah", "shorts", "story", "amithejerk"],
        "category": "22",
    },
    {
        "key": "batch3/short3_07.mp4",
        "file": str(OUTPUT_DIR / "batch3/short3_07.mp4"),
        "publish": datetime(2026, 4, 11, 17, 0, 0, tzinfo=timezone.utc),
        "title": "AITA for leaving my friend at the brewery? #shorts #reddit",
        "description": "Story from r/AmItheAsshole\n\n#shorts #reddit #aita #story",
        "tags": ["reddit", "aita", "shorts", "story", "amithejerk"],
        "category": "22",
    },
    {
        "key": "batch3/short3_08.mp4",
        "file": str(OUTPUT_DIR / "batch3/short3_08.mp4"),
        "publish": datetime(2026, 4, 12, 9, 0, 0, tzinfo=timezone.utc),
        "title": "AITAH husband cut off my son's hair so I used his card #shorts",
        "description": "Story from r/AITAH\n\n#shorts #reddit #aitah #story",
        "tags": ["reddit", "aitah", "shorts", "story", "amithejerk"],
        "category": "22",
    },
    {
        "key": "batch3/short3_09.mp4",
        "file": str(OUTPUT_DIR / "batch3/short3_09.mp4"),
        "publish": datetime(2026, 4, 12, 17, 0, 0, tzinfo=timezone.utc),
        "title": "AITA for telling my BIL to stop helping his sick friend? #shorts",
        "description": "Story from r/AmItheAsshole\n\n#shorts #reddit #aita #story",
        "tags": ["reddit", "aita", "shorts", "story", "amithejerk"],
        "category": "22",
    },
    {
        "key": "batch3/short3_10.mp4",
        "file": str(OUTPUT_DIR / "batch3/short3_10.mp4"),
        "publish": datetime(2026, 4, 13, 9, 0, 0, tzinfo=timezone.utc),
        "title": "AITA for drinking more beers than allowed at a party? #shorts",
        "description": "Story from r/AmItheAsshole\n\n#shorts #reddit #aita #story",
        "tags": ["reddit", "aita", "shorts", "story", "amithejerk"],
        "category": "22",
    },
    # ── Batch2 Reddit: Apr 13-17 (skip _04 _07 — duplicados do batch3) ───
    {
        "key": "batch2/short2_01.mp4",
        "file": str(OUTPUT_DIR / "batch2/short2_01.mp4"),
        "publish": datetime(2026, 4, 13, 17, 0, 0, tzinfo=timezone.utc),
        "title": "My husband genuinely disgusts me #shorts #reddit",
        "description": "Story from r/TrueOffMyChest\n\n#shorts #reddit #trueoffmychest #story",
        "tags": ["reddit", "trueoffmychest", "shorts", "story"],
        "category": "22",
    },
    {
        "key": "batch2/short2_02.mp4",
        "file": str(OUTPUT_DIR / "batch2/short2_02.mp4"),
        "publish": datetime(2026, 4, 14, 9, 0, 0, tzinfo=timezone.utc),
        "title": "AITA for saying my DIL isn't ready to be a parent? #shorts",
        "description": "Story from r/AmItheAsshole\n\n#shorts #reddit #aita #story",
        "tags": ["reddit", "aita", "shorts", "story", "amithejerk"],
        "category": "22",
    },
    {
        "key": "batch2/short2_03.mp4",
        "file": str(OUTPUT_DIR / "batch2/short2_03.mp4"),
        "publish": datetime(2026, 4, 14, 17, 0, 0, tzinfo=timezone.utc),
        "title": "AITA for implying my wife might have parasites? #shorts #reddit",
        "description": "Story from r/AmItheAsshole\n\n#shorts #reddit #aita #story",
        "tags": ["reddit", "aita", "shorts", "story", "amithejerk"],
        "category": "22",
    },
    {
        "key": "batch2/short2_05.mp4",
        "file": str(OUTPUT_DIR / "batch2/short2_05.mp4"),
        "publish": datetime(2026, 4, 15, 9, 0, 0, tzinfo=timezone.utc),
        "title": "They mocked me for locking my door so I stole a potato peeler #shorts",
        "description": "Story from r/pettyrevenge\n\n#shorts #reddit #pettyrevenge #story",
        "tags": ["reddit", "pettyrevenge", "shorts", "story", "maliciouscompliance"],
        "category": "22",
    },
    {
        "key": "batch2/short2_06.mp4",
        "file": str(OUTPUT_DIR / "batch2/short2_06.mp4"),
        "publish": datetime(2026, 4, 15, 17, 0, 0, tzinfo=timezone.utc),
        "title": "I should have been worried about my fiancé's friend #shorts",
        "description": "Story from r/TrueOffMyChest\n\n#shorts #reddit #trueoffmychest #story",
        "tags": ["reddit", "trueoffmychest", "shorts", "story"],
        "category": "22",
    },
    {
        "key": "batch2/short2_08.mp4",
        "file": str(OUTPUT_DIR / "batch2/short2_08.mp4"),
        "publish": datetime(2026, 4, 16, 9, 0, 0, tzinfo=timezone.utc),
        "title": "We set up a kettle in the bedroom for petty revenge #shorts",
        "description": "Story from r/pettyrevenge\n\n#shorts #reddit #pettyrevenge #maliciouscompliance #story",
        "tags": ["reddit", "pettyrevenge", "maliciouscompliance", "shorts", "story"],
        "category": "22",
    },
    {
        "key": "batch2/short2_09.mp4",
        "file": str(OUTPUT_DIR / "batch2/short2_09.mp4"),
        "publish": datetime(2026, 4, 16, 17, 0, 0, tzinfo=timezone.utc),
        "title": "TIFU by kissing my friend because I thought he was about to kiss me #shorts",
        "description": "Story from r/tifu\n\n#shorts #reddit #tifu #story",
        "tags": ["reddit", "tifu", "shorts", "story"],
        "category": "22",
    },
    {
        "key": "batch2/short2_10.mp4",
        "file": str(OUTPUT_DIR / "batch2/short2_10.mp4"),
        "publish": datetime(2026, 4, 17, 9, 0, 0, tzinfo=timezone.utc),
        "title": "TIFU by laughing at a celibacy poster at the wrong moment #shorts",
        "description": "Story from r/TrueOffMyChest\n\n#shorts #reddit #tifu #story",
        "tags": ["reddit", "tifu", "trueoffmychest", "shorts", "story"],
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
