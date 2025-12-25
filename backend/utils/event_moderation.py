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

    r"\bs[iı1!][kq]+\w*\b",
    r"\bs[iı1!][kq]+[iı1!][m]\w*\b",
    r"\bs[iı1!][kq]+[iı1!][kq]\w*\b",
    r"\bs[iı1!][kq]+[iı1!][kq][iı1!]\w*\b",
    r"\bs[iı1!][kq]+[iı1!][kq][iı1!][kq]\w*\b",
    r"\bs[iı1!][kq][iı1!][m][l][e]\b",
    r"\bam[cç][iı1!][kq]\w*\b",
    r"\bam[cç][iı1!][kq][iı1!]\w*\b",
    r"\bam[cç][iı1!][kq][iı1!][kq]\w*\b",
    r"\ba[qk]\b",
    r"\ba[mn][kq]\b",
    r"\bm[kq]\b",
    r"\bs[gğ]\b",
    r"\bs[gğ][t]\w*\b",
    r"\bo[cç]\b",
    r"\bo[cç][oö0]\w*\b",
    r"\bg[oö0]t+\w*\b",
    r"\bg[oö0]t[vw]e[r]+\w*\b",
    r"\bg[oö0]t[vw][e3][r]+[e3][n]\b",
    r"\bor[oö0]spu\w*\b",
    r"\bor[oö0]s[pb]u\w*\b",
    r"\by[a@][r]+a[kq]\b",
    r"\by[a@][r]+a[kq]\w*\b",
    r"\bta[sş]+a[kq]\b",
    r"\bta[sş]+a[kq]\w*\b",
    r"\bmal\b",
    r"\bsalak\b",
    r"\baptal\b",
    r"\bgerizekal[ıi]\b",
    r"\bgeri\s*zekal[ıi]\b",
    r"\bembesil\b",
    r"\bdangalak\b",
    r"\bşerefsiz\b",
    r"\bs1k1k\b",
    r"\bs1kik\b",
    r"\bs1kık\b",
    r"\bs[iı]k[iı]k\b",
    r"\bs[iı]k[iı]\w*\b",
    r"\bs1[kq]\w*\b",
    r"\bg0t\w*\b",
    r"\bor0spu\w*\b",
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
