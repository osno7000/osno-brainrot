"""
Video assembly: background + TTS audio + word-by-word captions.
Output: 1080x1920 (9:16) MP4 for YouTube Shorts.
"""
import json
import textwrap
from pathlib import Path
from moviepy import *
import numpy as np


# Shorts dimensions
WIDTH = 1080
HEIGHT = 1920
FPS = 30

# Caption styling
FONT_SIZE = 72
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
CAPTION_Y = 0.72  # 72% down the screen
MAX_WORDS_PER_CAPTION = 3  # Show N words at a time
CAPTION_COLOR = "white"
CAPTION_STROKE_COLOR = "black"
CAPTION_STROKE_WIDTH = 4

# Header bar
HEADER_TEXT = "r/{subreddit}"
HEADER_Y = 0.08


def make_gradient_bg(duration: float, color1=(20, 20, 40), color2=(40, 10, 60)) -> VideoClip:
    """Fallback: animated gradient background."""
    def make_frame(t):
        progress = (np.sin(t * 0.3) + 1) / 2
        r = int(color1[0] + (color2[0] - color1[0]) * progress)
        g = int(color1[1] + (color2[1] - color1[1]) * progress)
        b = int(color1[2] + (color2[2] - color1[2]) * progress)
        frame = np.full((HEIGHT, WIDTH, 3), [r, g, b], dtype=np.uint8)
        return frame
    return VideoClip(make_frame, duration=duration).with_fps(FPS)


def load_background(bg_path: str | None, duration: float) -> VideoClip:
    """Load background video or create gradient fallback."""
    if bg_path and Path(bg_path).exists():
        bg = VideoFileClip(bg_path)
        # Crop to 9:16
        target_ratio = WIDTH / HEIGHT
        current_ratio = bg.w / bg.h
        if current_ratio > target_ratio:
            new_w = int(bg.h * target_ratio)
            bg = bg.cropped(x_center=bg.w / 2, width=new_w)
        else:
            new_h = int(bg.w / target_ratio)
            bg = bg.cropped(y_center=bg.h / 2, height=new_h)
        bg = bg.resized((WIDTH, HEIGHT))
        # Loop if needed
        if bg.duration < duration:
            loops = int(duration / bg.duration) + 2
            bg = concatenate_videoclips([bg] * loops)
        bg = bg.subclipped(0, duration)
        return bg
    else:
        return make_gradient_bg(duration)


def build_caption_clips(words: list, duration: float) -> list:
    """
    Build word-by-word caption clips.
    Groups MAX_WORDS_PER_CAPTION words, shows each group for its duration.
    """
    clips = []
    i = 0
    while i < len(words):
        # Take a group of words
        group = words[i:i + MAX_WORDS_PER_CAPTION]
        group_text = " ".join(w["word"] for w in group)
        start = group[0]["start_ms"] / 1000
        end = group[-1]["end_ms"] / 1000

        # Clamp to video duration
        end = min(end, duration)
        if start >= duration:
            break

        clip_duration = max(end - start, 0.1)

        try:
            txt = TextClip(
                text=group_text,
                font=FONT,
                font_size=FONT_SIZE,
                color=CAPTION_COLOR,
                stroke_color=CAPTION_STROKE_COLOR,
                stroke_width=CAPTION_STROKE_WIDTH,
                method="caption",
                size=(WIDTH - 120, None),
            )
            txt = txt.with_start(start).with_duration(clip_duration)
            txt = txt.with_position(("center", int(HEIGHT * CAPTION_Y)))
            clips.append(txt)
        except Exception as e:
            print(f"  Caption error for '{group_text}': {e}")

        i += MAX_WORDS_PER_CAPTION

    return clips


def build_header(subreddit: str, duration: float) -> TextClip:
    """Top header showing subreddit name."""
    try:
        header = TextClip(
            text=f"r/{subreddit}",
            font=FONT,
            font_size=48,
            color="#FF4500",
            stroke_color="black",
            stroke_width=3,
        )
        header = header.with_duration(duration)
        header = header.with_position(("center", int(HEIGHT * HEADER_Y)))
        return header
    except Exception as e:
        print(f"  Header error: {e}")
        return None


def assemble(
    audio_path: str,
    timing_data: dict,
    output_path: str,
    subreddit: str = "tifu",
    bg_path: str = None,
) -> str:
    """Assemble the final video."""
    words = timing_data["words"]
    duration = timing_data.get("duration_s") or (words[-1]["end_ms"] / 1000 + 0.5 if words else 10)
    duration += 0.5  # Slight padding at end

    print(f"  Assembling {duration:.1f}s video...")

    # Background
    bg = load_background(bg_path, duration)

    # Audio
    audio = AudioFileClip(audio_path)

    # Captions
    print("  Building captions...")
    caption_clips = build_caption_clips(words, duration)
    print(f"  {len(caption_clips)} caption clips")

    # Header
    header = build_header(subreddit, duration)

    # Compose
    layers = [bg] + caption_clips
    if header:
        layers.append(header)

    final = CompositeVideoClip(layers, size=(WIDTH, HEIGHT))
    final = final.with_audio(audio)
    final = final.with_duration(duration)

    # Export
    output_path = str(output_path)
    print(f"  Rendering to {output_path}...")
    final.write_videofile(
        output_path,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        preset="fast",
        logger=None,
    )

    print(f"  Done: {output_path}")
    return output_path


if __name__ == "__main__":
    # Quick test with dummy data
    test_timing = {
        "duration_s": 5,
        "words": [
            {"word": "Hello", "start_ms": 0, "end_ms": 400},
            {"word": "world", "start_ms": 450, "end_ms": 800},
            {"word": "this", "start_ms": 900, "end_ms": 1100},
            {"word": "is", "start_ms": 1150, "end_ms": 1300},
            {"word": "a", "start_ms": 1350, "end_ms": 1450},
            {"word": "test", "start_ms": 1500, "end_ms": 2000},
        ]
    }
    print("Testing video assembly (no audio)...")
    # Can't test without real audio, but structure is correct
    print("Assembly module loaded OK")
