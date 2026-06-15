"""Analyze transcript for interesting moments — hooks, emotional, surprising, questions"""
import re

def analyze_moments(transcript: dict) -> list:
    """Detect interesting moments from transcript segments.
    Returns list of {start, end, type, text, score}"""
    segments = transcript.get("segments", [])
    moments = []
    
    for i, seg in enumerate(segments):
        text = seg.get("text", "").strip()
        if not text:
            continue
        score = 0
        types = []
        
        # 1. Strong hooks — short punchy statements
        if len(text.split()) <= 8 and text[-1] in ".!":
            score += 20
            types.append("hook")
        
        # 2. Questions
        if "?" in text:
            score += 25
            types.append("question")
        
        # 3. Exclamation / emphasis
        if text.endswith("!") or text.isupper():
            score += 30
            types.append("emphasis")
        
        # 4. Emotional keywords
        emotional_words = [
            "amazing", "incredible", "terrible", "awful", "love", "hate",
            "worst", "best", "never", "always", "shocked", "surprised",
            "crazy", "wow", "oh my god", "unbelievable", "disgusting",
            "beautiful", "perfect", "destroyed", "killed", "genius",
            "stupid", "brilliant", "horrible", "fantastic", "ridiculous",
            "epic", "legendary", "pathetic", "garbage", "insane"
        ]
        if any(w in text.lower() for w in emotional_words):
            score += 20
            types.append("emotional")
        
        # 5. Surprising — numbers, statistics, comparisons
        if re.search(r'\d+%|\$\d+|×\d+|x\d+|\d+ times|\d+ million|\d+ billion|\d+ thousand', text.lower()):
            score += 15
            types.append("surprising")
        
        # 6. Contrast / but / however / actually
        if re.search(r'\b(but|however|actually|wait|hold on|not really|suddenly)\b', text.lower()):
            score += 15
            types.append("contrast")
        
        # 7. Short punchy lines (sound-bite length)
        word_count = len(text.split())
        if 3 <= word_count <= 12:
            score += 10
        
        # 8. Imperative / command — "watch this", "check this out"
        if re.match(r'^(watch|check|look|see|try|get|guess|imagine|picture)', text.lower()):
            score += 15
            types.append("command")
        
        if score > 0:
            # Pad the segment slightly
            start = max(0, seg["start"] - 0.3)
            end = seg["end"] + 0.3
            moments.append({
                "start": round(start, 2),
                "end": round(end, 2),
                "text": text,
                "score": round(score / 30.0, 2),  # normalize to 0-1-ish
                "types": list(set(types))
            })
    
    # Sort by score descending, then take top
    moments.sort(key=lambda x: x["score"], reverse=True)
    return moments

def get_hooks(transcript: dict) -> list:
    """Get the first few segments as potential hooks"""
    segments = transcript.get("segments", [])
    hooks = []
    for i, seg in enumerate(segments[:10]):
        text = seg.get("text", "").strip()
        if len(text.split()) <= 15 and len(text) > 10:
            hooks.append({
                "start": seg["start"],
                "end": seg["end"],
                "text": text,
                "score": 0.5,
                "types": ["opening_hook"]
            })
    return hooks
