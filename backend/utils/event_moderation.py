import os
import json
import re
from openai import OpenAI

# -------------------------------------------------
# OpenAI client
# -------------------------------------------------
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# -------------------------------------------------
# HARD PROFANITY FILTER (FAIL-SAFE)
# -------------------------------------------------
# AI prompt bypass edilse bile bu kelimeler ASLA geçmez
PROFANITY_PATTERNS = [
    r"\bsik+\w*\b",
    r"\bg[oö]t+\w*\b",
    r"\bam(c|ç)[ıiuü]k?\w*\b",
    r"\bpiç\b",
    r"\bkahpe\b",
    r"\borospu\w*\b",
    r"\bsalak\b",
    r"\baptal\b",
    r"\bgerizekal[ıi]\b",
    r"\bmal\b",
    r"\bsiktir\b",
    r"\bsikerim\b",
]

def contains_profanity(text: str) -> bool:
    """
    Regex-based hard profanity detection.
    """
    if not text:
        return False

    text = text.lower()
    for pattern in PROFANITY_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return True
    return False


# -------------------------------------------------
# MAIN MODERATION FUNCTION
# -------------------------------------------------
def review_event_content(title: str, description: str) -> dict:
    """
    Reviews event content using:
    1) HARD profanity filter (regex)
    2) OpenAI semantic moderation

    Returns:
    {
        "is_safe": bool,
        "flags": {
            "sexism": bool,
            "political": bool,
            "profanity": bool
        },
        "reason": str | None
    }
    """

    combined_text = f"{title}\n{description}"

    # ---------- 1. HARD FILTER ----------
    if contains_profanity(combined_text):
        return {
            "is_safe": False,
            "flags": {
                "sexism": False,
                "political": False,
                "profanity": True
            },
            "reason": "Content contains profanity or insult (hard filter)"
        }

    # ---------- 2. AI MODERATION ----------
    try:
        system_prompt = """
You are a STRICT content moderation system.

Analyze the given event title and description.

Flag content if it contains:
- Sexual insults or explicit sexual expressions
- Hate speech, insults, or profanity (even mild)
- Sexist or gender-discriminatory language
- Political propaganda or aggressive political messaging

Rules:
- If there is ANY doubt, set is_safe = false
- Be conservative
- Context does NOT excuse profanity
- Respond ONLY with valid JSON

Required JSON schema:
{
  "is_safe": true | false,
  "flags": {
    "sexism": true | false,
    "political": true | false,
    "profanity": true | false
  },
  "reason": "short explanation or null"
}
"""

        user_prompt = f"""
Event title:
{title}

Event description:
{description}
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.0,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )

        content = response.choices[0].message.content.strip()
        parsed = json.loads(content)

        # Schema validation
        if not isinstance(parsed, dict):
            raise ValueError("Invalid AI response")

        flags = parsed.get("flags", {})

        is_safe = bool(parsed.get("is_safe", False))

        # Extra safety: profanity flag ALWAYS blocks
        if flags.get("profanity") is True:
            is_safe = False

        return {
            "is_safe": is_safe,
            "flags": {
                "sexism": bool(flags.get("sexism")),
                "political": bool(flags.get("political")),
                "profanity": bool(flags.get("profanity")),
            },
            "reason": parsed.get("reason")
        }

    except Exception:
        # ---------- FAIL CLOSED ----------
        # AI çökerse event ASLA publish edilmez
        return {
            "is_safe": False,
            "flags": {
                "sexism": False,
                "political": False,
                "profanity": True
            },
            "reason": "Content moderation service unavailable"
        }
