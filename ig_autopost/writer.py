"""Write carousel copy in Hinglish with the Gemini API (free tier is enough for 1 post/day)."""
import json
import os
import re
import time

import requests

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

PROMPT = """You write Instagram carousel posts for "Super Deals India", an Indian smart-shopping page.
Audience: Indian online shoppers (18-35) who buy on Amazon, Flipkart, Myntra, Meesho.
Language: natural Hinglish (Hindi in Roman script mixed with simple English), friendly, punchy, like a smart elder sibling.

Today's post
- Pillar: {pillar}
- Topic: {topic}
- Hook idea: {hook}
- Points to cover, in this order (one slide each): {points}

STRICT RULES
1. Write exactly {n} slides, one per point above, same order.
2. Do NOT invent facts: no specific prices, percentages, statistics, sale dates, laws, or brand/model claims
   unless they appear in the topic/points above. Use general, always-true advice. Illustrative examples are OK
   only if clearly hypothetical (e.g. "maan lo ₹999 ka product...").
3. No medical, legal or financial guarantees. No "guaranteed", "100%", "best ever".
4. No emojis inside slide text (caption may use a few).
5. Length limits (characters): cover_kicker <= 14, cover_title <= 40, cover_sub <= 95,
   heading <= 32, body <= 170, tip <= 65, caption <= 700.
6. cover_kicker: a very short eye-catching phrase/number from the hook (e.g. "70% OFF", "20000 mAh", "108MP").
   Set cover_strike true ONLY if the kicker is something the post debunks (fake/myth). Use "" if nothing fits.
7. Caption: 3-5 short lines in Hinglish: a hook line, what they'll learn, then
   "Save karo next shopping ke liye 📌" and "Daily deals → link in bio".
8. hashtags: 8-12 relevant tags, no '#' symbol, lowercase, mix of Hinglish/English (e.g. smartshopping, onlineshoppingindia).

Return ONLY JSON in this exact shape:
{{"cover_kicker": "", "cover_strike": false, "cover_title": "", "cover_sub": "",
  "slides": [{{"heading": "", "body": "", "tip": ""}}],
  "caption": "", "hashtags": [""]}}
"""

LIMITS = {"cover_kicker": 18, "cover_title": 48, "cover_sub": 110}
SLIDE_LIMITS = {"heading": 40, "body": 200, "tip": 80}


def _call_gemini(prompt: str) -> str:
    key = os.environ["GEMINI_API_KEY"]
    model = os.environ.get("GEMINI_MODEL") or "gemini-3.6-flash"
    r = requests.post(
        GEMINI_URL.format(model=model),
        headers={"x-goog-api-key": key, "Content-Type": "application/json"},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.8},
        },
        timeout=90,
    )
    r.raise_for_status()
    data = r.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


def _validate(c: dict, n: int) -> list:
    problems = []
    for k, lim in LIMITS.items():
        if not isinstance(c.get(k), str):
            problems.append(f"{k} missing")
        elif len(c[k]) > lim:
            problems.append(f"{k} too long ({len(c[k])}>{lim})")
    if not c.get("cover_title"):
        problems.append("cover_title empty")
    slides = c.get("slides")
    if not isinstance(slides, list) or len(slides) != n:
        problems.append(f"need exactly {n} slides")
    else:
        for i, s in enumerate(slides, 1):
            for k, lim in SLIDE_LIMITS.items():
                v = s.get(k)
                if not isinstance(v, str) or not v.strip():
                    problems.append(f"slide {i} {k} empty")
                elif len(v) > lim:
                    problems.append(f"slide {i} {k} too long ({len(v)}>{lim})")
    if not isinstance(c.get("caption"), str) or not c["caption"].strip():
        problems.append("caption empty")
    if not isinstance(c.get("hashtags"), list):
        problems.append("hashtags missing")
    return problems


def write_post(row: dict) -> dict:
    points = [p.strip() for p in row["points"].split("|") if p.strip()]
    prompt = PROMPT.format(pillar=row["pillar"], topic=row["topic"], hook=row["hook"],
                           points="; ".join(f"{i}) {p}" for i, p in enumerate(points, 1)),
                           n=len(points))
    last_err = None
    for attempt in range(3):
        try:
            raw = _call_gemini(prompt)
            raw = re.sub(r"^```(json)?|```$", "", raw.strip()).strip()
            c = json.loads(raw)
            problems = _validate(c, len(points))
            if not problems:
                c["pillar"] = row["pillar"]
                c["topic"] = row["topic"]
                c["hashtags"] = [h.strip().lstrip("#").replace(" ", "") for h in c["hashtags"] if h.strip()][:12]
                return c
            last_err = "; ".join(problems)
            prompt += f"\n\nYour previous answer was rejected: {last_err}. Fix these and return JSON again."
        except Exception as e:  # network / JSON errors
            last_err = repr(e)
        time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"Gemini could not produce valid post content: {last_err}")


def build_caption(c: dict) -> str:
    tags = " ".join(f"#{h}" for h in c["hashtags"])
    return f"{c['caption'].strip()}\n\n.\n.\n{tags}"[:2200]
