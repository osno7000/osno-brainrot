"""
TTS generation using Fish Audio API + faster-whisper for word-level timing.
Replaces edge-tts for brainrot videos with higher quality voices (Stewie, Peter Griffin, etc.)
"""
import json
import re
import requests
from pathlib import Path

# Fish Audio config
FISH_API_URL = "https://api.fish.audio/v1/tts"
KEY_PATH = Path.home() / "mind/credentials/fish_audio_api_key.txt"

# Voice reference IDs
VOICES = {
    "stewie": "e91c4f5974f149478a35affe820d02ac",
    # Peter Griffin — raspy/nasal New England accent, energetic (tested 2026-04-01)
    "peter": "e34b4e061b874623a08f41e5c4fecfb9",
}

# Whisper model (tiny = fast, base = better accuracy)
WHISPER_MODEL_SIZE = "tiny"
_whisper_model = None  # lazy-loaded


def _get_key():
    try:
        return KEY_PATH.read_text().strip()
    except Exception:
        raise RuntimeError(f"Fish Audio API key not found at {KEY_PATH}")


def _get_whisper():
    global _whisper_model
    if _whisper_model is None:
        print("  Loading Whisper model (first run may take a moment)...")
        from faster_whisper import WhisperModel
        _whisper_model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
    return _whisper_model


def clean_text(text: str) -> str:
    """Clean Reddit post text for TTS."""
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'~~(.+?)~~', r'\1', text)
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
    text = re.sub(r'#+\s+', '', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def generate_audio(text: str, audio_path: str, voice: str = "stewie") -> int:
    """
    Call Fish Audio API to generate TTS audio.
    Returns file size in bytes.
    """
    ref_id = VOICES.get(voice)
    if not ref_id:
        raise ValueError(f"Unknown voice: {voice}. Available: {list(VOICES.keys())}")

    key = _get_key()
    payload = {
        "text": text,
        "reference_id": ref_id,
        "format": "mp3",
        "latency": "normal",
    }

    resp = requests.post(
        FISH_API_URL,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=120,
    )

    if resp.status_code == 402:
        raise RuntimeError("Fish Audio: insufficient credits. Top up at fish.audio/app/billing")
    resp.raise_for_status()

    with open(audio_path, "wb") as f:
        f.write(resp.content)

    return len(resp.content)


def get_word_timing(audio_path: str) -> list:
    """
    Use faster-whisper to extract word-level timing from audio.
    Returns list of {word, start_ms, end_ms} dicts.
    """
    model = _get_whisper()
    segments, info = model.transcribe(
        audio_path,
        word_timestamps=True,
        language="en",
    )

    words = []
    for segment in segments:
        if segment.words:
            for w in segment.words:
                word = w.word.strip()
                if word:
                    words.append({
                        "word": word,
                        "start_ms": int(w.start * 1000),
                        "end_ms": int(w.end * 1000),
                    })

    return words


def generate(text: str, output_dir: str, voice: str = "stewie") -> dict:
    """
    Main entry point. Generates TTS audio + word timing.
    Returns same format as generate_tts.generate() for compatibility.
    """
    text = clean_text(text)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    audio_path = str(output_dir / "tts_audio.mp3")

    # Step 1: Generate TTS audio via Fish Audio
    print(f"  Calling Fish Audio API (voice: {voice})...")
    size = generate_audio(text, audio_path, voice=voice)
    print(f"  Audio generated: {size:,} bytes → {audio_path}")

    # Step 2: Get word timing via whisper
    print("  Transcribing for word timing...")
    words = get_word_timing(audio_path)
    print(f"  {len(words)} words timed")

    # Get actual audio duration via ffprobe (more accurate than whisper end time)
    import subprocess
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", audio_path],
            capture_output=True, text=True, timeout=10
        )
        actual_audio_dur = float(r.stdout.strip())
        # assemble_video.py adds 0.5s padding — pass duration slightly under audio length
        # so assembled video stays within audio bounds
        duration = max(actual_audio_dur - 0.6, actual_audio_dur * 0.9)
    except Exception:
        duration = words[-1]["end_ms"] / 1000 if words else 0

    # Save timing data
    timing_path = str(output_dir / "tts_timing.json")
    with open(timing_path, "w") as f:
        json.dump({"text": text, "words": words}, f, indent=2)

    return {
        "audio_path": audio_path,
        "timing_path": timing_path,
        "words": words,
        "duration_s": duration,
        "text": text,
    }


if __name__ == "__main__":
    import sys
    text = sys.argv[1] if len(sys.argv) > 1 else (
        "So today I completely failed. I put my laptop in the washing machine "
        "because I confused it with my lunchbox. It is currently on spin cycle. "
        "My boss is going to kill me."
    )
    print("Testing Fish Audio TTS...")
    result = generate(text, "/tmp/fish_tts_test", voice="stewie")
    print(f"Done! Duration: {result['duration_s']:.1f}s")
    print(f"First 3 words: {result['words'][:3]}")
