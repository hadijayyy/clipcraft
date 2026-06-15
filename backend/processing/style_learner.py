"""Style learning — saves/loads user preferences for clipping style"""
import json
import os
from typing import Optional

STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage")
STYLE_FILE = os.path.join(STORAGE_DIR, "user_style.json")

def save_style(name: str, settings: dict) -> dict:
    """Save a style profile"""
    styles = load_all_styles()
    styles[name] = {
        "name": name,
        "settings": settings,
        **settings
    }
    with open(STYLE_FILE, "w") as f:
        json.dump(styles, f, indent=2)
    return styles[name]

def load_style(name: str) -> Optional[dict]:
    """Load a specific style profile"""
    styles = load_all_styles()
    return styles.get(name)

def load_all_styles() -> dict:
    """Load all saved style profiles"""
    if not os.path.exists(STYLE_FILE):
        return {}
    try:
        with open(STYLE_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def delete_style(name: str) -> bool:
    """Delete a style profile"""
    styles = load_all_styles()
    if name in styles:
        del styles[name]
        with open(STYLE_FILE, "w") as f:
            json.dump(styles, f, indent=2)
        return True
    return False

def learn_from_example(clip_data: dict) -> dict:
    """Extract style settings from a clip example"""
    style = {
        "clip_duration_preference": clip_data.get("end", 60) - clip_data.get("start", 0),
        "has_subtitles": bool(clip_data.get("subtitles")),
        "text_overlay_count": len(clip_data.get("overlays", [])),
        "source": clip_data.get("source", "manual"),
    }
    return style
