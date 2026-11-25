"""Asset graphics manager with base64 caching for high-speed rendering in Streamlit HTML components."""

import base64
import os
from functools import lru_cache

GRAPHICS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "graphics")

@lru_cache(maxsize=32)
def get_graphic_data_uri(name: str) -> str:
    """Returns a base64 data URI for an image in assets/graphics/."""
    filename = name if name.endswith((".jpg", ".png", ".webp")) else f"{name}.jpg"
    path = os.path.join(GRAPHICS_DIR, filename)
    if os.path.exists(path):
        with open(path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")
            ext = os.path.splitext(filename)[1].lstrip(".").lower()
            if ext == "jpg":
                ext = "jpeg"
            return f"data:image/{ext};base64,{encoded}"
    return ""
