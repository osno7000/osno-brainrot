"""
TTS generation using edge-tts with word-level timing for captions.
"""
import asyncio
import edge_tts
import json
import re
from pathlib import Path


VOICE = "en-US-GuyNeural"
RATE = "+20%"  # slightly faster = more brainrot energy
VOLUME = "+0%"


def clean_text(text: str) -> str:
    """Clean Reddit post text for TTS."""
    # Remove markdown
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'~~(.+?)~~', r'\1', text)
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
    text = re.sub(r'#+\s+', '', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()
    return text


async def generate_tts_with_timing(text: str, output_dir: Path, voice: str = VOICE) -> dict:
    """
    Generate TTS audio + word timing data.
    Returns: {audio_path, words: [{word, start_ms, end_ms}]}
    """
    text = clean_text(text)
    output_dir = Path(output_dir)
    audio_path = output_dir / "tts_audio.mp3"
    timing_path = output_dir / "tts_timing.json"

    audio_bytes = bytearray()
    words = []

    communicate = edge_tts.Communicate(text, voice, rate=RATE, volume=VOLUME, boundary="WordBoundary")
    submaker = edge_tts.SubMaker()

    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_bytes.extend(chunk["data"])
        elif chunk["type"] == "WordBoundary":
            submaker.feed(chunk)
            # offset is in 100-nanosecond units
            start_ms = chunk["offset"] // 10000
            duration_ms = chunk["duration"] // 10000
            words.append({
                "word": chunk["text"],
                "start_ms": start_ms,
                "end_ms": start_ms + duration_ms
            })

    # Save audio
    with open(audio_path, "wb") as f:
        f.write(audio_bytes)

    # Save timing
    timing_data = {"text": text, "words": words}
    with open(timing_path, "w") as f:
        json.dump(timing_data, f, indent=2)

    total_duration = words[-1]["end_ms"] / 1000 if words else 0
    print(f"  TTS generated: {len(words)} words, {total_duration:.1f}s")

    return {
        "audio_path": str(audio_path),
        "timing_path": str(timing_path),
        "words": words,
        "duration_s": total_duration,
        "text": text
    }


def generate(text: str, output_dir: str, voice: str = VOICE) -> dict:
    return asyncio.run(generate_tts_with_timing(text, Path(output_dir), voice))


if __name__ == "__main__":
    import sys
    text = sys.argv[1] if len(sys.argv) > 1 else (
        "So today I totally failed. I put my work laptop in the washing machine "
        "because I confused it with my lunchbox. It's currently on spin cycle. "
        "TIFU big time. My boss is going to kill me."
    )
    result = generate(text, "/tmp/tts_test")
    print(json.dumps(result["words"][:5], indent=2))
