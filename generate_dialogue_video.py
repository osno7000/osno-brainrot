#!/usr/bin/env python3
"""
Peter Griffin + Stewie Griffin teaching dialogue brainrot video generator.

Format:
- Minecraft parkour background
- Stewie teaches Peter a real topic (investing, tech hacks, life tips)
- Character PNG shown when speaking (left=Peter, right=Stewie)
- Word-by-word captions at bottom center
- Audio sped up 1.3x for fast-paced feel
"""
import json
import os
import random
import subprocess
import tempfile
from pathlib import Path

import requests
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import *

# === CONFIG ===
WIDTH, HEIGHT = 1080, 1920
FPS = 30
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
AUDIO_SPEED = 1.3  # 30% faster for brainrot energy

# Character face card dimensions
CARD_W, CARD_H = 380, 180
CARD_Y = int(HEIGHT * 0.62)  # vertical position of character cards

# Caption config
CAPTION_Y = int(HEIGHT * 0.80)
CAPTION_FONT_SIZE = 68
MAX_WORDS_PER_CAPTION = 3

# Fish Audio
FISH_API_URL = "https://api.fish.audio/v1/tts"
KEY_PATH = Path.home() / "mind/credentials/fish_audio_api_key.txt"
VOICES = {
    "peter": "e34b4e061b874623a08f41e5c4fecfb9",
    "stewie": "e91c4f5974f149478a35affe820d02ac",
}
CHAR_COLORS = {
    "peter":  {"bg": (30, 80, 180),   "text": (255, 255, 255), "name": "PETER"},
    "stewie": {"bg": (180, 30, 30),   "text": (255, 255, 255), "name": "STEWIE"},
}

# PNG images (placed in characters/ folder)
CHAR_IMG_DIR = Path(__file__).parent / "characters"
CHAR_IMGS = {
    "peter": CHAR_IMG_DIR / "peter.png",
    "stewie": CHAR_IMG_DIR / "stewie.png",
}
CHAR_IMG_W = 320
CHAR_IMG_H = 380

BG_DIR = Path(__file__).parent / "backgrounds"
OUTPUT_DIR = Path(__file__).parent / "output"


# ── TOPICS LIBRARY ───────────────────────────────────────────────────────────
# Format: Stewie teaches → Peter asks dumb question → Stewie explains sharply
# Keep lines SHORT — 1-2 sentences max

TOPICS = [
    {
        "id": "compound_interest",
        "lines": [
            {"speaker": "stewie", "text": "Peter. One hundred euros a month. Thirty years. Eight percent return. How much do you end up with?"},
            {"speaker": "peter",  "text": "Uh... three thousand six hundred euros? I did the math."},
            {"speaker": "stewie", "text": "One hundred and fifty thousand euros. That's compound interest. Your money makes money."},
            {"speaker": "peter",  "text": "That's not real. You made that up."},
            {"speaker": "stewie", "text": "It's literally math, you fathead. Start ten years earlier and you DOUBLE the result."},
            {"speaker": "peter",  "text": "So I should've started when I was born?"},
            {"speaker": "stewie", "text": "The second best time is NOW. Index fund. Whatever you can afford. Even fifty euros a month."},
            {"speaker": "peter",  "text": "What's an index fund?"},
            {"speaker": "stewie", "text": "Oh for the love— subscribe and I'll explain EVERYTHING. You clearly need constant supervision."},
        ]
    },
    {
        "id": "salary_negotiation",
        "lines": [
            {"speaker": "stewie", "text": "Peter. Never. EVER. Give your salary number first in a job interview."},
            {"speaker": "peter",  "text": "I always say what I make. Isn't that honest?"},
            {"speaker": "stewie", "text": "It's not honesty. It's handing them a ceiling. Whoever names the number first LOSES."},
            {"speaker": "peter",  "text": "So what do I say when they ask?"},
            {"speaker": "stewie", "text": "Say: I'm sure you have a budget for this role. What is it? Force THEM to go first."},
            {"speaker": "peter",  "text": "What if they won't?"},
            {"speaker": "stewie", "text": "Then give a range where the BOTTOM is what you actually want. Not the top. The bottom."},
            {"speaker": "peter",  "text": "That's... actually smart. Why did nobody tell me this?"},
            {"speaker": "stewie", "text": "Because companies LOVE people like you. Subscribe before your next interview. Seriously."},
        ]
    },
    {
        "id": "cashback_hack",
        "lines": [
            {"speaker": "stewie", "text": "Peter. Are you using a cashback credit card for your daily spending?"},
            {"speaker": "peter",  "text": "No, I just use cash. Cash is normal."},
            {"speaker": "stewie", "text": "You're leaving hundreds of euros on the table every year. For FREE money you just don't take."},
            {"speaker": "peter",  "text": "Credit cards are dangerous. You spend more."},
            {"speaker": "stewie", "text": "Only if you're an idiot. Get a cashback card. Spend ONLY what you already spend. Pay full balance monthly."},
            {"speaker": "peter",  "text": "And that's it?"},
            {"speaker": "stewie", "text": "That's it. One percent to two percent back on everything. Groceries. Gas. Beer. Your stupid Pawtucket tickets."},
            {"speaker": "peter",  "text": "So they pay ME to buy beer?"},
            {"speaker": "stewie", "text": "Essentially yes. Subscribe. There are more tricks like this that your bank definitely doesn't want you to know."},
        ]
    },
    {
        "id": "4_percent_rule",
        "lines": [
            {"speaker": "stewie", "text": "Peter. What if I told you there's a number. And when you hit it, you never have to work again?"},
            {"speaker": "peter",  "text": "Is it a billion? It's a billion isn't it."},
            {"speaker": "stewie", "text": "No you moron. Take your yearly expenses. Multiply by twenty-five. That's your number."},
            {"speaker": "peter",  "text": "Wait, that's it?"},
            {"speaker": "stewie", "text": "The four percent rule. You withdraw four percent per year. Historically your portfolio never runs out."},
            {"speaker": "peter",  "text": "So if I spend thirty thousand a year I need... seven hundred and fifty thousand?"},
            {"speaker": "stewie", "text": "First intelligent thing you've said. Yes. Invest now, hit that number, retire. Simple."},
            {"speaker": "peter",  "text": "That seems too simple."},
            {"speaker": "stewie", "text": "It IS simple. People just don't start. Subscribe. Your retirement thanks you later."},
        ]
    },
    {
        "id": "keyboard_shortcuts",
        "lines": [
            {"speaker": "stewie", "text": "Peter. How long does it take you to find a file on your computer?"},
            {"speaker": "peter",  "text": "I don't know. I just click around until I find it. Could be five minutes."},
            {"speaker": "stewie", "text": "Windows key plus E. File Explorer opens instantly. Control plus F searches inside any app."},
            {"speaker": "peter",  "text": "I knew Control C and Control V."},
            {"speaker": "stewie", "text": "Control Z undoes anything. Control Shift T reopens a closed browser tab. Win plus D shows desktop."},
            {"speaker": "peter",  "text": "I've been doing this wrong my whole life."},
            {"speaker": "stewie", "text": "Alt F4 closes any window. And yes, you can apply that to your boss in a meeting."},
            {"speaker": "peter",  "text": "That last one doesn't actually work on people."},
            {"speaker": "stewie", "text": "Unfortunately not. Subscribe for more shortcuts that actually work."},
        ]
    },
    {
        "id": "inflation_cash",
        "lines": [
            {"speaker": "stewie", "text": "Peter. You have ten thousand euros sitting in a bank account doing nothing. Do you know what inflation is doing to it?"},
            {"speaker": "peter",  "text": "Keeping it safe?"},
            {"speaker": "stewie", "text": "Destroying it. Three percent inflation per year. Ten years later, your ten thousand is worth seven thousand in real value."},
            {"speaker": "peter",  "text": "But the number on the screen still says ten thousand."},
            {"speaker": "stewie", "text": "That's the trick. The number stays. The BUYING POWER shrinks. Same money, fewer goods."},
            {"speaker": "peter",  "text": "So saving money is bad?"},
            {"speaker": "stewie", "text": "Holding CASH is bad. Invest it. Even a money market fund beats inflation. A savings account in Portugal pays almost nothing."},
            {"speaker": "peter",  "text": "How do I know what to invest in?"},
            {"speaker": "stewie", "text": "Subscribe. That's literally tomorrow's lesson. And please, for the love of god, move your money."},
        ]
    },
    {
        "id": "sleep_debt",
        "lines": [
            {"speaker": "stewie", "text": "Peter. You cannot catch up on sleep. Sleep debt is permanent cognitive damage."},
            {"speaker": "peter",  "text": "I sleep in on weekends. I thought that fixed it."},
            {"speaker": "stewie", "text": "It doesn't. You feel better but the performance deficit persists. Studies are clear on this."},
            {"speaker": "peter",  "text": "So what, I just have to sleep eight hours every night?"},
            {"speaker": "stewie", "text": "Seven to nine. Consistent schedule. Same time every day including weekends. No exceptions."},
            {"speaker": "peter",  "text": "That sounds miserable."},
            {"speaker": "stewie", "text": "You know what's more miserable? Being forty percent less productive every day for your entire adult life."},
            {"speaker": "peter",  "text": "Is that the number?"},
            {"speaker": "stewie", "text": "After seventeen hours awake your brain runs like you're drunk. Subscribe. Sleep. In that order."},
        ]
    },
]


# ── dialogue builder ──────────────────────────────────────────────────────────

def build_dialogue_from_topic(topic: dict) -> list[dict]:
    """Return the lines list from a topic dict."""
    return topic["lines"]


def get_random_topic() -> dict:
    return random.choice(TOPICS)


def get_topic_by_id(topic_id: str) -> dict:
    for t in TOPICS:
        if t["id"] == topic_id:
            return t
    raise ValueError(f"Topic not found: {topic_id}. Available: {[t['id'] for t in TOPICS]}")


# ── helpers ───────────────────────────────────────────────────────────────────

def _get_key():
    return KEY_PATH.read_text().strip()


def _ffprobe_duration(path):
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, timeout=10
    )
    return float(r.stdout.strip())


def speed_up_audio(input_path: str, output_path: str, factor: float = AUDIO_SPEED) -> float:
    """Speed up audio file using ffmpeg atempo filter. Returns new duration."""
    # atempo range: 0.5 to 2.0. For factor > 2 need chaining.
    if factor <= 2.0:
        atempo = f"atempo={factor}"
    else:
        # Chain two atempo filters
        f1 = min(factor, 2.0)
        f2 = factor / f1
        atempo = f"atempo={f1},atempo={f2}"

    subprocess.run(
        ["ffmpeg", "-y", "-i", input_path,
         "-filter:a", atempo,
         output_path],
        capture_output=True, check=True
    )
    return _ffprobe_duration(output_path)


# ── TTS generation ────────────────────────────────────────────────────────────

def generate_line_tts(text: str, speaker: str, out_path: str) -> float:
    """Generate TTS for one dialogue line. Returns actual audio duration."""
    key = _get_key()
    resp = requests.post(
        FISH_API_URL,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"text": text, "reference_id": VOICES[speaker],
              "format": "mp3", "latency": "normal"},
        timeout=120,
    )
    if resp.status_code == 402:
        raise RuntimeError("Fish Audio: no credits")
    resp.raise_for_status()
    with open(out_path, "wb") as f:
        f.write(resp.content)
    return _ffprobe_duration(out_path)


def get_word_timing(audio_path: str) -> list[dict]:
    """Use faster-whisper to get word-level timing."""
    from faster_whisper import WhisperModel
    model = WhisperModel("tiny", device="cpu", compute_type="int8")
    segments, _ = model.transcribe(audio_path, word_timestamps=True, language="en")
    words = []
    for seg in segments:
        if seg.words:
            for w in seg.words:
                word = w.word.strip()
                if word:
                    words.append({
                        "word": word,
                        "start_ms": int(w.start * 1000),
                        "end_ms": int(w.end * 1000),
                    })
    return words


# ── character image ───────────────────────────────────────────────────────────

def make_char_image(speaker: str) -> np.ndarray:
    """Load character PNG, resize, add name label. Returns RGBA numpy array."""
    img_path = CHAR_IMGS.get(speaker)

    if img_path and img_path.exists():
        try:
            img = Image.open(img_path).convert("RGBA")
            img.thumbnail((CHAR_IMG_W, CHAR_IMG_H), Image.LANCZOS)
            label_h = 60
            canvas = Image.new("RGBA", (CHAR_IMG_W, CHAR_IMG_H + label_h), (0, 0, 0, 0))
            x_off = (CHAR_IMG_W - img.width) // 2
            canvas.paste(img, (x_off, 0), img)

            draw = ImageDraw.Draw(canvas)
            c = CHAR_COLORS[speaker]
            draw.rounded_rectangle(
                [10, CHAR_IMG_H + 4, CHAR_IMG_W - 10, CHAR_IMG_H + label_h - 4],
                radius=12, fill=c["bg"] + (220,)
            )
            try:
                font = ImageFont.truetype(FONT, 36)
            except Exception:
                font = ImageFont.load_default()
            name = c["name"]
            bbox = draw.textbbox((0, 0), name, font=font)
            tw = bbox[2] - bbox[0]
            draw.text(
                ((CHAR_IMG_W - tw) // 2, CHAR_IMG_H + 14),
                name, fill=c["text"], font=font
            )
            return np.array(canvas)
        except Exception as e:
            print(f"  Warning: could not load {img_path}: {e}")

    # Fallback: colored text card
    c = CHAR_COLORS[speaker]
    img = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([0, 0, CARD_W - 1, CARD_H - 1], radius=24, fill=c["bg"] + (230,))
    try:
        font_large = ImageFont.truetype(FONT, 72)
    except Exception:
        font_large = ImageFont.load_default()
    name = c["name"]
    bbox = draw.textbbox((0, 0), name, font=font_large)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((CARD_W - tw) // 2, (CARD_H - th) // 2), name, fill=c["text"], font=font_large)
    return np.array(img)


# ── video assembly ────────────────────────────────────────────────────────────

def build_char_clip(speaker: str, start: float, duration: float) -> ImageClip:
    """Build a character image clip at correct screen position."""
    arr = make_char_image(speaker)
    h, w = arr.shape[:2]
    clip = ImageClip(arr, duration=duration).with_start(start)
    # Peter bottom-left, Stewie bottom-right
    x = 20 if speaker == "peter" else WIDTH - w - 20
    y = CARD_Y - h // 2
    return clip.with_position((x, y))


def build_caption_clips(words: list[dict], duration: float) -> list:
    """Word-by-word captions."""
    clips = []
    i = 0
    while i < len(words):
        group = words[i:i + MAX_WORDS_PER_CAPTION]
        group_text = " ".join(w["word"] for w in group)
        start = group[0]["start_ms"] / 1000
        end = min(group[-1]["end_ms"] / 1000, duration)
        if start >= duration:
            break
        clip_dur = max(end - start, 0.1)
        try:
            txt = TextClip(
                text=group_text,
                font=FONT,
                font_size=CAPTION_FONT_SIZE,
                color="white",
                stroke_color="black",
                stroke_width=4,
                method="caption",
                size=(WIDTH - 120, None),
            )
            txt = txt.with_start(start).with_duration(clip_dur)
            txt = txt.with_position(("center", CAPTION_Y))
            clips.append(txt)
        except Exception as e:
            print(f"  caption err: {e}")
        i += MAX_WORDS_PER_CAPTION
    return clips


def load_background(duration: float) -> VideoClip:
    """Load a background video from backgrounds/ folder, looping as needed."""
    bg_files = list(BG_DIR.glob("*.mp4")) + list(BG_DIR.glob("*.webm"))
    if not bg_files:
        def make_frame(t):
            c = int(20 + 20 * np.sin(t * 0.3))
            return np.full((HEIGHT, WIDTH, 3), [c, c // 2, c * 2], dtype=np.uint8)
        return VideoClip(make_frame, duration=duration).with_fps(FPS)

    bg_path = str(random.choice(bg_files))
    bg = VideoFileClip(bg_path)

    # Crop to 9:16
    target_ratio = WIDTH / HEIGHT
    if bg.w / bg.h > target_ratio:
        new_w = int(bg.h * target_ratio)
        bg = bg.cropped(x_center=bg.w / 2, width=new_w)
    else:
        new_h = int(bg.w / target_ratio)
        bg = bg.cropped(y_center=bg.h / 2, height=new_h)
    bg = bg.resized((WIDTH, HEIGHT))

    if bg.duration < duration:
        loops = int(duration / bg.duration) + 2
        bg = concatenate_videoclips([bg] * loops)
    return bg.subclipped(0, duration)


# ── main pipeline ─────────────────────────────────────────────────────────────

def generate(topic_id: str = None, output_path: str = None) -> str:
    """
    Full pipeline: topic → Peter+Stewie dialogue → video.
    If topic_id is None, picks a random topic.
    Returns output_path.
    """
    OUTPUT_DIR.mkdir(exist_ok=True)

    if topic_id:
        topic = get_topic_by_id(topic_id)
    else:
        topic = get_random_topic()

    if output_path is None:
        output_path = str(OUTPUT_DIR / f"peter_stewie_{topic['id']}.mp4")

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)

        print(f"\n[0] Topic: {topic['id']}")
        lines = build_dialogue_from_topic(topic)
        for l in lines:
            print(f"  {l['speaker'].upper()}: {l['text'][:70]}")

        print(f"\n[1] Generating TTS for {len(lines)} lines...")
        raw_audio_files = []
        sped_audio_files = []
        durations = []

        for i, line in enumerate(lines):
            raw_path = str(tmp / f"raw_{i:02d}_{line['speaker']}.mp3")
            sped_path = str(tmp / f"sped_{i:02d}_{line['speaker']}.mp3")
            print(f"  Line {i+1}/{len(lines)}: {line['speaker']}...")
            dur_raw = generate_line_tts(line["text"], line["speaker"], raw_path)
            dur_sped = speed_up_audio(raw_path, sped_path, AUDIO_SPEED)
            sped_audio_files.append(sped_path)
            durations.append(dur_sped)
            print(f"    raw={dur_raw:.1f}s → sped={dur_sped:.1f}s")

        print("\n[2] Concatenating audio with gaps...")
        GAP = 0.20  # seconds between lines (shorter = faster feel)
        inputs = []
        filter_parts = []
        for i, f in enumerate(sped_audio_files):
            inputs += ["-i", f]
            filter_parts.append(f"[{i}]apad=pad_dur={GAP}[p{i}]")

        silence_filters = ";".join(filter_parts)
        chain = "".join(f"[p{i}]" for i in range(len(sped_audio_files)))
        full_filter = f"{silence_filters};{chain}concat=n={len(sped_audio_files)}:v=0:a=1[out]"
        concat_path = str(tmp / "dialogue_full.mp3")

        subprocess.run(
            ["ffmpeg", "-y"] + inputs +
            ["-filter_complex", full_filter, "-map", "[out]", concat_path],
            capture_output=True, check=True
        )
        actual_dur = _ffprobe_duration(concat_path)
        print(f"  Total audio: {actual_dur:.1f}s")

        print("\n[3] Getting word timing for captions...")
        all_words = get_word_timing(concat_path)
        print(f"  {len(all_words)} words timed")

        print("\n[4] Building speaker timeline...")
        speaker_timeline = []
        t = 0.0
        for i, line in enumerate(lines):
            end = t + durations[i]
            speaker_timeline.append({
                "speaker": line["speaker"],
                "start": t,
                "end": end,
            })
            t = end + GAP

        print("\n[5] Assembling video...")
        video_dur = actual_dur - 0.3

        bg = load_background(video_dur + 0.5)
        bg = bg.subclipped(0, video_dur)
        audio = AudioFileClip(concat_path).subclipped(0, video_dur)

        # Character clips
        char_clips = []
        for seg in speaker_timeline:
            if seg["start"] >= video_dur:
                break
            end = min(seg["end"], video_dur)
            dur = end - seg["start"]
            if dur <= 0:
                continue
            char_clips.append(build_char_clip(seg["speaker"], seg["start"], dur))

        # Caption clips
        cap_clips = build_caption_clips(all_words, video_dur)
        print(f"  {len(cap_clips)} caption clips, {len(char_clips)} character clips")

        layers = [bg] + char_clips + cap_clips
        final = CompositeVideoClip(layers, size=(WIDTH, HEIGHT))
        final = final.with_audio(audio)
        final = final.with_duration(video_dur)

        print(f"\n[6] Rendering to {output_path}...")
        final.write_videofile(
            output_path,
            fps=FPS,
            codec="libx264",
            audio_codec="aac",
            preset="fast",
            logger=None,
        )

    size = os.path.getsize(output_path)
    print(f"\nDone: {output_path} ({size/1024/1024:.1f}MB, {video_dur:.1f}s)")
    return output_path


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    topic_id = sys.argv[1] if len(sys.argv) > 1 else None

    if topic_id == "--list":
        print("Available topics:")
        for t in TOPICS:
            print(f"  {t['id']}")
        sys.exit(0)

    out = str(OUTPUT_DIR / f"peter_stewie_{topic_id or 'random'}.mp4")
    generate(topic_id=topic_id, output_path=out)
