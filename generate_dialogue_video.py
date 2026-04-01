#!/usr/bin/env python3
"""
Peter Griffin + Stewie Griffin dialogue brainrot video generator.

Format:
- Minecraft parkour background
- Reddit post split into Peter/Stewie alternating dialogue
- Character face card shown when speaking (left=Peter, right=Stewie)
- Word-by-word captions at bottom center
"""
import json
import os
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

BG_DIR = Path(__file__).parent / "backgrounds"
OUTPUT_DIR = Path(__file__).parent / "output"


# ── helpers ────────────────────────────────────────────────────────────────

def _get_key():
    return KEY_PATH.read_text().strip()


def _ffprobe_duration(path):
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, timeout=10
    )
    return float(r.stdout.strip())


# ── dialogue script builder ─────────────────────────────────────────────────

def build_dialogue(title: str, body: str) -> list[dict]:
    """
    Convert Reddit post into Peter/Stewie dialogue lines.
    Returns list of {speaker, text} dicts.
    """
    # Split body into sentences / logical chunks (~3-5 sentences each)
    import re
    sentences = re.split(r'(?<=[.!?])\s+', body.strip())
    sentences = [s.strip() for s in sentences if s.strip()]

    lines = []

    # Opening — Peter reads title
    lines.append({"speaker": "peter",
                  "text": f"So Stewie, check this out. {title}"})

    # Stewie reacts
    lines.append({"speaker": "stewie",
                  "text": "Oh God, what idiotic human drama have you stumbled upon now?"})

    # Alternate body paragraphs
    chunk_size = max(1, len(sentences) // 3)
    chunks = [" ".join(sentences[i:i+chunk_size])
              for i in range(0, len(sentences), chunk_size)]

    for i, chunk in enumerate(chunks[:4]):
        if i % 2 == 0:
            lines.append({"speaker": "peter", "text": chunk})
        else:
            lines.append({"speaker": "stewie",
                          "text": f"Fascinating. {chunk}"})

    # Stewie's verdict
    reactions = [
        "You are absolutely the jerk here. Utterly, magnificently the jerk.",
        "Not the jerk. The other party is clearly suffering from acute idiocy.",
        "I cannot believe you're even asking. Everyone sucks here. Spectacular failure all around.",
        "You're the jerk. Though I must say, impressively so.",
    ]
    verdict = reactions[len(lines) % len(reactions)]
    lines.append({"speaker": "stewie", "text": verdict})

    # Peter's outro
    lines.append({"speaker": "peter",
                  "text": "Comment below who you think is the jerk. And like and subscribe!"})

    return lines


# ── TTS generation ──────────────────────────────────────────────────────────

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


def get_word_timing(audio_path: str, text: str) -> list[dict]:
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


def concat_audio(mp3_files: list[str], out_path: str, gaps: list[float] = None) -> float:
    """Concatenate MP3 files with optional silence gaps. Returns total duration."""
    if gaps is None:
        gaps = [0.3] * (len(mp3_files) - 1)

    # Use ffmpeg to concat
    inputs = []
    filter_parts = []
    for i, f in enumerate(mp3_files):
        inputs += ["-i", f]
        filter_parts.append(f"[{i}]")

    # Build concat filter
    n = len(mp3_files)
    filter_str = "".join(filter_parts) + f"concat=n={n}:v=0:a=1[out]"
    cmd = ["ffmpeg", "-y"] + inputs + [
        "-filter_complex", filter_str,
        "-map", "[out]",
        out_path
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return _ffprobe_duration(out_path)


# ── character card image ────────────────────────────────────────────────────

def make_char_card(speaker: str) -> np.ndarray:
    """
    Create a character card image (PIL → numpy array for moviepy).
    Returns RGBA numpy array of shape (CARD_H, CARD_W, 4).
    """
    c = CHAR_COLORS[speaker]
    img = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Rounded rectangle background
    radius = 24
    draw.rounded_rectangle([0, 0, CARD_W - 1, CARD_H - 1],
                            radius=radius, fill=c["bg"] + (230,))

    # Character name
    try:
        font_large = ImageFont.truetype(FONT, 72)
        font_small = ImageFont.truetype(FONT, 28)
    except Exception:
        font_large = ImageFont.load_default()
        font_small = font_large

    name = c["name"]
    # Center name vertically in the card
    bbox = draw.textbbox((0, 0), name, font=font_large)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = (CARD_W - tw) // 2
    ty = (CARD_H - th) // 2 - 10
    draw.text((tx, ty), name, fill=c["text"], font=font_large)

    # Subtitle
    sub = "Family Guy"
    bbox2 = draw.textbbox((0, 0), sub, font=font_small)
    sw = bbox2[2] - bbox2[0]
    draw.text(((CARD_W - sw) // 2, ty + th + 8), sub,
              fill=c["text"] + (160,), font=font_small)

    return np.array(img)


# ── video assembly ──────────────────────────────────────────────────────────

def build_char_clip(speaker: str, start: float, duration: float,
                    is_peter: bool) -> ImageClip:
    """Build a character card clip at correct screen position."""
    arr = make_char_card(speaker)
    clip = ImageClip(arr, duration=duration).with_start(start)
    # Peter left, Stewie right
    if is_peter:
        x = 40
    else:
        x = WIDTH - CARD_W - 40
    clip = clip.with_position((x, CARD_Y))
    return clip


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
        # Gradient fallback
        def make_frame(t):
            c = int(20 + 20 * np.sin(t * 0.3))
            return np.full((HEIGHT, WIDTH, 3), [c, c // 2, c * 2], dtype=np.uint8)
        return VideoClip(make_frame, duration=duration).with_fps(FPS)

    import random
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


# ── main pipeline ───────────────────────────────────────────────────────────

def generate(title: str, body: str, output_path: str, subreddit: str = "AITA") -> str:
    """
    Full pipeline: Reddit post → Peter+Stewie dialogue → video.
    Returns output_path.
    """
    import re

    OUTPUT_DIR.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)

        print("\n[1] Building dialogue script...")
        lines = build_dialogue(title, body)
        for l in lines:
            print(f"  {l['speaker'].upper()}: {l['text'][:60]}...")

        print("\n[2] Generating TTS for each line...")
        audio_files = []
        durations = []
        for i, line in enumerate(lines):
            ap = str(tmp / f"line_{i:02d}_{line['speaker']}.mp3")
            print(f"  Line {i+1}/{len(lines)}: {line['speaker']}...")
            dur = generate_line_tts(line["text"], line["speaker"], ap)
            audio_files.append(ap)
            durations.append(dur)
            print(f"    → {dur:.1f}s")

        print("\n[3] Concatenating audio...")
        concat_path = str(tmp / "dialogue_full.mp3")
        gaps = [0.25] * (len(audio_files) - 1)
        total_dur = sum(durations) + sum(gaps)

        # Build concat with gaps (silence between lines)
        # Use ffmpeg concat filter
        inputs = []
        filter_parts = []
        for i, f in enumerate(audio_files):
            inputs += ["-i", f]
            filter_parts.append(f"[{i}]apad=pad_dur=0.25[p{i}]")
        silence_filters = ";".join(filter_parts)
        chain = "".join(f"[p{i}]" for i in range(len(audio_files)))
        full_filter = f"{silence_filters};{chain}concat=n={len(audio_files)}:v=0:a=1[out]"
        subprocess.run(
            ["ffmpeg", "-y"] + inputs +
            ["-filter_complex", full_filter, "-map", "[out]", concat_path],
            capture_output=True, check=True
        )
        actual_dur = _ffprobe_duration(concat_path)
        print(f"  Total audio: {actual_dur:.1f}s")

        print("\n[4] Getting word timing for captions...")
        all_words = get_word_timing(concat_path, "")
        print(f"  {len(all_words)} words timed")

        print("\n[5] Building character timing map...")
        # Figure out when each speaker is active (by cumulative time)
        speaker_timeline = []  # list of {speaker, start, end}
        t = 0.0
        for i, line in enumerate(lines):
            end = t + durations[i]
            speaker_timeline.append({
                "speaker": line["speaker"],
                "start": t,
                "end": end,
            })
            t = end + 0.25  # gap

        print("\n[6] Assembling video...")
        video_dur = actual_dur - 0.3  # slight trim to avoid audio overrun

        # Background
        bg = load_background(video_dur + 0.5)
        bg = bg.subclipped(0, video_dur)

        # Audio
        audio = AudioFileClip(concat_path).subclipped(0, video_dur)

        # Character cards
        char_clips = []
        for seg in speaker_timeline:
            if seg["start"] >= video_dur:
                break
            end = min(seg["end"], video_dur)
            dur = end - seg["start"]
            if dur <= 0:
                continue
            is_peter = seg["speaker"] == "peter"
            clip = build_char_clip(seg["speaker"], seg["start"], dur, is_peter)
            char_clips.append(clip)

        # Captions
        cap_clips = build_caption_clips(all_words, video_dur)
        print(f"  {len(cap_clips)} caption clips, {len(char_clips)} character clips")

        # Compose
        layers = [bg] + char_clips + cap_clips
        final = CompositeVideoClip(layers, size=(WIDTH, HEIGHT))
        final = final.with_audio(audio)
        final = final.with_duration(video_dur)

        print(f"\n[7] Rendering to {output_path}...")
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


# ── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Test with a sample AITA post
    title = "AITA for refusing to pay for my roommate's cat's vet bill after my dog scared it?"
    body = (
        "So my roommate has a cat named Whiskers and I have a dog named Rex. "
        "We agreed when we moved in that the animals would stay in their respective rooms. "
        "Last week my roommate left the cat door open by mistake and Rex got excited "
        "and chased Whiskers under the couch. The cat was scared and knocked over a lamp. "
        "Now my roommate says Whiskers has been having anxiety issues and wants me to pay "
        "for the vet bill of two hundred dollars. I said no because she left the door open. "
        "She's not speaking to me now. My other friends are split on this."
    )

    out = str(Path(__file__).parent / "output" / "peter_stewie_test.mp4")
    generate(title, body, out, subreddit="AITA")
