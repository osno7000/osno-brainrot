# osno-brainrot

YouTube Shorts generator: top Reddit posts → brainrot video with TTS + word-by-word captions + Minecraft background.

## What it does

1. Fetches top posts from r/tifu, r/AmItheAsshole, r/maliciouscompliance, etc.
2. Generates TTS audio with word-level timing via Microsoft Edge TTS
3. Assembles 9:16 video (1080x1920) with:
   - Looping gameplay background (Minecraft parkour or any MP4)
   - Word-by-word caption overlay synced to audio
   - Subreddit header
4. Outputs MP4 ready for YouTube Shorts

## Usage

```bash
pip install -r requirements.txt

# Generate from random Reddit post
python3 main.py

# Test mode
python3 main.py --test

# Custom subreddit + background
python3 main.py --subreddit tifu maliciouscompliance --bg backgrounds/minecraft.mp4
```

## Setup

Drop any `.mp4` background videos into `backgrounds/`. If none found, uses animated gradient fallback.

Tested on: Ubuntu, Python 3.12, no GPU required.

## Dependencies

- `edge-tts` — Microsoft neural TTS (free, no API key)
- `moviepy` — video assembly
- `praw` — Reddit API (optional, currently uses public JSON)
