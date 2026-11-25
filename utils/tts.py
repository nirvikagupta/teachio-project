"""Convert text to speech and save as MP3."""
from __future__ import annotations
from pathlib import Path
import uuid

def text_to_speech(text: str, output_dir: Path) -> Path:
    """Generate MP3 from text using gTTS. Returns path to the file."""
    try:
        from gtts import gTTS
    except ImportError:
        raise RuntimeError("gTTS not installed. Run: pip install gTTS")

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"podcast_{uuid.uuid4().hex[:8]}.mp3"
    tts = gTTS(text=text, lang="en", slow=False)
    tts.save(str(out_path))
    return out_path