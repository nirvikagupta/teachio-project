"""Extract text from uploaded PDFs for study prompts."""

from __future__ import annotations

import hashlib
from pathlib import Path


def unit_material_fingerprint(paths: list[Path]) -> str:
    parts: list[str] = []
    for p in sorted(paths, key=lambda x: str(x)):
        try:
            st = p.stat()
            parts.append(f"{p.name}:{int(st.st_mtime)}")
        except OSError:
            parts.append(p.name)
    raw = "|".join(parts).encode("utf-8", errors="replace")
    return hashlib.sha256(raw).hexdigest()[:16]


def extract_text_from_pdf(path: Path, max_chars: int) -> tuple[str, int]:
    """Return (extracted_text, character_count)."""
    try:
        from pypdf import PdfReader
    except ImportError:
        return f"[Install pypdf to read PDFs: pip install pypdf]\n", 0

    chunks: list[str] = []
    n = 0
    try:
        reader = PdfReader(str(path))
        for page in reader.pages:
            if n >= max_chars:
                break
            t = page.extract_text() or ""
            take = t[: max(0, max_chars - n)]
            chunks.append(take)
            n += len(take)
    except Exception as e:
        chunks.append(f"\n[Could not read {path.name}: {e}]\n")
    return "".join(chunks), n


def extract_unit_combined_text(paths: list[Path], max_chars: int = 4096) -> str:
    """Concatenate text from all PDFs in stable order, capped at max_chars."""
    if not paths:
        return ""
    parts: list[str] = []
    total = 0
    for p in paths:
        if total >= max_chars:
            break
        remaining = max_chars - total
        block, used = extract_text_from_pdf(p, remaining)
        header = f"\n\n--- File: {p.name} ---\n"
        if total + len(header) + len(block) > max_chars:
            room = max(0, max_chars - total - len(header))
            block = block[:room]
        parts.append(header + block)
        total += len(header) + len(block)
    text = "".join(parts).strip()
    if not text:
        return (
            "[No extractable text from PDFs — they may be scanned images. "
            "Agents will use your subject and unit title only.]"
        )
    return text
