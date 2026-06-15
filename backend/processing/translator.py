"""Multi-language caption translation using OpenCode Zen Go / Google Translate"""

import os
import json
import subprocess

# AI config for translation
AI_BASE_URL = os.getenv("AI_BASE_URL", "https://opencode.ai/zen/go/v1")
AI_API_KEY = os.getenv("AI_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL", "qwen3.5-plus")

SUPPORTED_LANGUAGES = {
    "id": "Indonesian",
    "en": "English",
    "ms": "Malay",
    "th": "Thai",
    "vi": "Vietnamese",
    "tl": "Filipino",
    "ja": "Japanese",
    "ko": "Korean",
    "zh": "Chinese (Simplified)",
    "ar": "Arabic",
    "hi": "Hindi",
    "es": "Spanish",
    "pt": "Portuguese",
    "fr": "French",
    "de": "German",
    "ru": "Russian",
    "tr": "Turkish",
    "it": "Italian",
    "nl": "Dutch",
    "pl": "Polish",
}


def get_supported_languages() -> dict:
    """Return list of supported translation languages."""
    return SUPPORTED_LANGUAGES


def translate_srt(segments: list, target_lang: str) -> str:
    """Translate SRT segments to target language.
    
    Args:
        segments: List of {start, end, text} dicts
        target_lang: Target language code (e.g., 'id', 'ja', 'ko')
    
    Returns:
        SRT format string with translated text
    """
    if target_lang not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Unsupported language: {target_lang}. Use: {list(SUPPORTED_LANGUAGES.keys())}")
    
    if not segments:
        return ""
    
    # Build transcript for translation
    texts = [s.get("text", "") for s in segments]
    
    # Try AI translation first
    if AI_API_KEY:
        try:
            translated_texts = _translate_with_ai(texts, target_lang)
        except Exception:
            translated_texts = _translate_with_google(texts, target_lang)
    else:
        translated_texts = _translate_with_google(texts, target_lang)
    
    # Build SRT
    srt_lines = []
    for i, (seg, translated) in enumerate(zip(segments, translated_texts), 1):
        start = _format_srt_time(seg.get("start", 0))
        end = _format_srt_time(seg.get("end", 0))
        srt_lines.append(f"{i}")
        srt_lines.append(f"{start} --> {end}")
        srt_lines.append(translated)
        srt_lines.append("")
    
    return "\n".join(srt_lines)


def _translate_with_ai(texts: list, target_lang: str) -> list:
    """Translate using OpenCode Zen Go AI."""
    import requests
    
    lang_name = SUPPORTED_LANGUAGES.get(target_lang, target_lang)
    
    prompt = f"""Translate the following text segments to {lang_name}.
Return ONLY a JSON array of translated strings, one for each input segment.
Do not add any explanation or markdown formatting.

Input texts:
{json.dumps(texts, ensure_ascii=False)}

Output:"""

    headers = {
        "Authorization": f"Bearer {AI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": AI_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }
    
    resp = requests.post(
        f"{AI_BASE_URL}/chat/completions",
        headers=headers,
        json=payload,
        timeout=30
    )
    resp.raise_for_status()
    
    result = resp.json()
    content = result.get("choices", [{}])[0].get("message", {}).get("content", "[]")
    
    # Parse JSON response
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    
    translated = json.loads(content)
    
    if len(translated) != len(texts):
        raise ValueError("Translation length mismatch")
    
    return translated


def _translate_with_google(texts: list, target_lang: str) -> list:
    """Fallback: translate using Google Translate (free, no API key)."""
    try:
        from deep_translator import GoogleTranslator
        translator = GoogleTranslator(source='auto', target=target_lang)
        return [translator.translate(t) if t else "" for t in texts]
    except ImportError:
        # If deep_translator not installed, return original
        return texts


def _format_srt_time(seconds: float) -> str:
    """Convert seconds to SRT time format (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
