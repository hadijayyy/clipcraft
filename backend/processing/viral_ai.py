"""Gemini AI Viral Analysis — find best clip segments from transcript.
Uses OpenCode Zen Go (or any OpenAI-compatible endpoint) with Gemini-style prompting."""

import os
import json

# AI config — uses OpenCode Zen Go by default
AI_BASE_URL = os.getenv("AI_BASE_URL", "https://opencode.ai/zen/go/v1")
AI_API_KEY = os.getenv("AI_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL", "qwen3.5-plus")


def analyze_viral_segments(transcript: dict, video_url: str = "", top_n: int = 5) -> list:
    """Use AI to find the most viral-worthy segments from a transcript.
    Returns list of {start, end, title, score, description, captions}."""

    segments = transcript.get("segments", [])
    if not segments:
        return []

    # Build transcript text with timestamps
    transcript_text = ""
    for seg in segments:
        transcript_text += f"[{seg['start']:.1f}s - {seg['end']:.1f}s] {seg['text']}\n"

    duration = segments[-1]['end'] if segments else 0

    prompt = f"""You are a viral content analyst for short-form video (TikTok, Instagram Reels, YouTube Shorts).

Analyze this video transcript and identify the TOP {top_n} most viral-worthy segments.

TRANSCRIPT (video duration: {duration:.0f}s):
{transcript_text}

For each segment, provide:
1. A catchy, clickbait short-form title (max 60 chars)
2. Exact start time in seconds (within the video duration)
3. Exact end time in seconds (15-60 seconds duration)
4. Virality/Hook Score (80-100, where 100 = guaranteed viral)
5. Brief description of why this segment will perform well
6. 2-3 high-impact caption lines with relative time offsets from segment start

Rules:
- Segments should be 15-60 seconds long
- Prioritize: emotional moments, surprising facts, strong hooks, quotable lines
- Each segment must be self-contained (makes sense without context)
- Captions should be punchy, uppercase, attention-grabbing

Return ONLY valid JSON in this exact format:
{{
  "clips": [
    {{
      "title": "String",
      "startTime": 0.0,
      "endTime": 30.0,
      "hookScore": 95,
      "description": "String",
      "captions": [
        {{"text": "CAPTION TEXT", "startOffset": 0.0, "endOffset": 5.0}}
      ]
    }}
  ]
}}"""

    try:
        import requests

        headers = {
            "Authorization": f"Bearer {AI_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": AI_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 2000
        }

        resp = requests.post(
            f"{AI_BASE_URL}/chat/completions",
            json=payload,
            headers=headers,
            timeout=60
        )

        if resp.status_code == 200:
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            # Parse JSON from response
            parsed = parse_ai_json(content)
            if parsed and "clips" in parsed:
                clips = parsed["clips"]
                # Add IDs
                for i, clip in enumerate(clips):
                    clip['id'] = f'ai-clip-{i}-{int(clip.get("startTime", 0))}'
                return clips
        else:
            print(f"[Gemini] API error: {resp.status_code} - {resp.text[:200]}")

    except Exception as e:
        print(f"[Gemini] Analysis failed: {e}")

    # Fallback: rule-based analysis
    return rule_based_analysis(transcript, top_n)


def parse_ai_json(text: str) -> dict:
    """Extract JSON from AI response, handling markdown code blocks."""
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting from code block
    import re
    json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try finding JSON object
    json_match = re.search(r'\{[^{}]*"clips"[^{}]*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    return {}


def rule_based_analysis(transcript: dict, top_n: int = 5) -> list:
    """Fallback rule-based viral analysis when AI is unavailable."""
    import re

    segments = transcript.get("segments", [])
    moments = []

    emotional_words = [
        "amazing", "incredible", "terrible", "awful", "love", "hate",
        "worst", "best", "never", "always", "shocked", "surprised",
        "crazy", "wow", "unbelievable", "disgusting", "beautiful",
        "perfect", "destroyed", "genius", "stupid", "brilliant",
        "horrible", "fantastic", "ridiculous", "epic", "legendary"
    ]

    for i, seg in enumerate(segments):
        text = seg.get("text", "").strip()
        if not text:
            continue

        score = 0
        types = []

        # Hook detection
        if len(text.split()) <= 8 and text[-1] in ".!":
            score += 20
            types.append("hook")

        # Questions
        if "?" in text:
            score += 25
            types.append("question")

        # Emphasis
        if text.endswith("!") or text.isupper():
            score += 30
            types.append("emphasis")

        # Emotional keywords
        if any(w in text.lower() for w in emotional_words):
            score += 20
            types.append("emotional")

        # Numbers/statistics
        if re.search(r'\d+%|\$\d+|\d+ times|\d+ million', text.lower()):
            score += 15
            types.append("surprising")

        # Contrast words
        if re.search(r'\b(but|however|actually|wait|hold on|suddenly)\b', text.lower()):
            score += 15
            types.append("contrast")

        if score > 0:
            moments.append({
                'text': text,
                'start': seg['start'],
                'end': seg['end'],
                'score': score,
                'types': types
            })

    # Group into clips (merge adjacent high-score segments)
    moments.sort(key=lambda x: x['score'], reverse=True)
    clips = []

    for m in moments[:top_n * 2]:
        # Create 15-45 second clip around this moment
        clip_start = max(0, m['start'] - 5)
        clip_end = min(segments[-1]['end'] if segments else 0, m['start'] + 30)

        # Check overlap with existing clips
        overlap = False
        for existing in clips:
            if clip_start < existing['endTime'] and clip_end > existing['startTime']:
                overlap = True
                break

        if not overlap:
            clips.append({
                'id': f'rule-clip-{len(clips)}-{int(m["start"])}',
                'title': f"🔥 {m['text'][:50]}",
                'startTime': round(clip_start, 1),
                'endTime': round(clip_end, 1),
                'hookScore': min(99, 70 + m['score'] // 5),
                'description': f"High-engagement moment: {', '.join(m['types'])}",
                'captions': [
                    {'text': m['text'].upper()[:50], 'startOffset': 0, 'endOffset': min(5, clip_end - clip_start)}
                ]
            })

            if len(clips) >= top_n:
                break

    return clips


def analyze_with_gemini(transcript: dict, api_key: str = None) -> list:
    """Analyze transcript using Google Gemini API directly.
    Falls back to OpenCode Zen Go or rule-based analysis."""
    if api_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.0-flash')

            segments = transcript.get("segments", [])
            transcript_text = "\n".join(
                f"[{s['start']:.1f}s] {s['text']}" for s in segments
            )

            prompt = f"""Analyze this transcript and find the top 5 most viral segments for TikTok/Reels.
Return JSON with clips array, each having: title, startTime, endTime, hookScore (80-100), description, captions.

TRANSCRIPT:
{transcript_text}"""

            response = model.generate_content(prompt)
            parsed = parse_ai_json(response.text)
            return parsed.get("clips", [])
        except Exception as e:
            print(f"[Gemini Direct] Error: {e}")

    # Use OpenCode Zen Go
    return analyze_viral_segments(transcript)
