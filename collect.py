"""
Collect r/worldcup posts and comments from Arctic Shift (public Reddit archive).
Labels each example using the decision hierarchy from planning.md.
Outputs: data.csv  (text, label, notes, source, ai_prelabel)
"""

import requests
import csv
import time
import re
import sys
from pathlib import Path

HEADERS = {"User-Agent": "worldcup-classification-dataset/1.0 (academic; codepath project)"}
BASE = "https://arctic-shift.photon-reddit.com/api"
OUT = Path(__file__).parent / "data.csv"

# ---------------------------------------------------------------------------
# Noise filter — remove logistics, spam, meta, pure questions
# ---------------------------------------------------------------------------

NOISE_RE = re.compile(
    r"\b(ticket|tickets|streaming|iptv|subscription|t[- ]shirt|jersey|merchandise|"
    r"souvenir|for sale|selling my|looking for|fan.?fest|fan.?zone|hotel|airbnb|"
    r"best gift|great gift|perfect gift|promo|discount|coupon|"
    r"how (do|can|should) (i|we)\b|where can (i|we)\b|"
    r"anyone (know|else have|selling|going to|attending)|"
    r"this sub(reddit)?|r\/worldcup|r\/soccer|"
    r"i('m| am) (watching|vacation|travel|visit)|"
    r"(download|watch|stream).{0,20}(free|online|live))\b",
    re.I,
)


def is_noise(text: str) -> bool:
    if NOISE_RE.search(text):
        return True
    stripped = text.strip()
    # Drop posts that are primarily a question (end with ? and no declarative sentence)
    sentences = re.split(r'[.!]', stripped)
    declarative = [s.strip() for s in sentences if s.strip() and not s.strip().endswith('?')]
    if not declarative and stripped.endswith('?'):
        return True
    return False


# ---------------------------------------------------------------------------
# Labeling — implements decision hierarchy from planning.md Section 3
# ---------------------------------------------------------------------------

CAUSAL_RE = re.compile(
    r"\b(because|since\b|due to|result(?:ed|s) in|explains?|which means|"
    r"this is why|the reason|shows? that|demonstrates?|therefore|thus\b|"
    r"as a result|leading to|caused|that'?s why|which is why|means that|"
    r"allowing them|enabled|allowed|forced|helped|prevented|contributed)\b",
    re.I,
)

TACTICAL_RE = re.compile(
    r"\b(possession|pressing|press\b|formation|shape\b|system\b|"
    r"offside trap|high line|defensive block|counterattack|counter.?press|"
    r"half.?space|through ball|progressive pass|xg\b|expected goal|"
    r"wing.?back|inverted winger|deep block|low block|high press|"
    r"build.?up|transition\b|high line|compactness|overload|"
    r"(back|line of) (three|four|five|3|4|5)|\d-\d-\d|\d-\d-\d-\d)\b",
    re.I,
)

STATS_RE = re.compile(
    r"\b\d+[\.,]?\d*\s*(goal|shot|save|pass|assist|touch|minute|cap|clean sheet|%|km|km/h)\b|"
    r"\b(top|bottom|first|second|third|fourth)\s+(in|of)\s+(the\s+)?(world|europe|group|tournament)\b|"
    r"\bfifa (ranking|world ranking)\b|"
    r"\b(world cup|tournament|competition)\s+record\b|"
    r"\b(in|since)\s+(19|20)\d{2}\b|"
    r"\b(only|just|more than|at least|fewer than)\s+\d+\s+(time|year|game|match|tournament)\b",
    re.I,
)

# Emotional words specifically about soccer events (not generic spam enthusiasm)
SOCCER_REACTION_RE = re.compile(
    r"\b(omg|wtf|omfg|lmao|lmfao|holy\s*(shit|cow|moly)|"
    r"unbelievable|incredible|insane|no way|are you kidding|"
    r"what a (goal|save|miss|tackle|foul|game|match|half|performance)|"
    r"i (still |just )?can'?t (believe|even)|"   # fixed: allow "still"/"just" between
    r"that (ref(eree)?|var|call|decision|penalty|foul|goal|save|tackle)|"
    r"robbery|robbed|rigged|disgrace|scandal|outrageous|"
    r"(yess+|nooo+|come on|let'?s go|bruh)\b|"
    r"GOOOAL|this is (insane|crazy|unreal)|what just happened|"
    r"(that was|this was)\s+(horrible|terrible|awful|a (joke|disgrace|nightmare|travesty))|"
    r"(heart|gut)[ -]?wrenching|jaw.?drop|stunned|speechless)\b",
    re.I,
)


def label_text(text: str):
    t = text.strip()
    words = t.split()
    n = len(words)

    if n < 6:
        return None, "too short"
    if is_noise(t):
        return None, "noise"

    tl = t.lower()
    causal   = bool(CAUSAL_RE.search(tl))
    tactical = bool(TACTICAL_RE.search(tl))
    stats    = bool(STATS_RE.search(tl))
    fact_count = int(tactical) + int(stats)

    exclamations = t.count("!")
    emotional    = bool(SOCCER_REACTION_RE.search(t))
    caps_words   = sum(1 for w in words if w.isupper() and len(w) > 2)

    # Soccer performance/evaluation language — distinguishes genuine analysis from
    # causal statements in questions or informational posts
    evaluation = bool(re.search(
        r"\b(won|lost|played (well|poorly|badly|brilliantly|terribly)|"
        r"performed|dominated|struggled|failed|succeeded|proved|"
        r"better|worse|stronger|weaker|effective|ineffective|"
        r"excellent|poor|great|terrible|impressive|disappointing|"
        r"outplayed|outclassed|underperformed|overperformed|"
        r"solid|shaky|clinical|wasteful|inconsistent|dominant|"
        r"defend(ing|ed)|attack(ing|ed)|control(led)?|dictate(d)?)\b",
        tl,
    ))

    # ── Analysis ──────────────────────────────────────────────────────────────
    is_analysis = n >= 15 and (
        (causal and fact_count >= 1) or
        (causal and tactical) or
        (fact_count >= 2) or
        (tactical and n >= 25) or
        # Conversational analysis: causal reasoning + soccer evaluation language
        # e.g. "France won because they defended deeper and controlled transitions"
        (causal and evaluation and n >= 20 and not emotional)
    )

    # ── Reaction ──────────────────────────────────────────────────────────────
    # Short soccer-specific emotional response — NOT spam or generic enthusiasm
    is_reaction = not is_analysis and (
        # Soccer-specific emotional language, short
        (emotional and n <= 50) or
        # Very short ALL-CAPS burst (e.g. "WHAT A GOAL MESSI!!!")
        (caps_words >= 2 and exclamations >= 1 and n <= 20) or
        # Multiple exclamations in a short, passionate post
        (exclamations >= 3 and n <= 25)
    )

    # ── Notes ─────────────────────────────────────────────────────────────────
    notes = ""
    if causal and fact_count == 0 and is_analysis:
        notes = "causal language, no specific stats – borderline Analysis/Hot Take"
    elif stats and not causal and not is_reaction:
        notes = "single stat only – Hot Take per decision rule"
    elif is_analysis and exclamations > 0:
        notes = "analytical with emotional markers"
    elif emotional and n > 50 and not is_analysis:
        notes = "emotional but too long for Reaction – Hot Take"

    if is_analysis:
        return "Analysis", notes
    if is_reaction:
        return "Reaction", notes
    return "Hot Take", notes


# ---------------------------------------------------------------------------
# Collection
# ---------------------------------------------------------------------------

SKIP_TITLE_RE = re.compile(
    r"^\[(Match Thread|Post Match|Pre Match|Match Prediction|Video|Photo|"
    r"Image|Highlight|GIF|Goal|Discussion Thread|Weekly|Official|Megathread)\]",
    re.I,
)


def is_opinion_title(title: str) -> bool:
    if SKIP_TITLE_RE.match(title.strip()):
        return False
    if re.match(r"^(Official|Breaking|Confirmed|Squad|Group Stage|Result|Score|Line.?up|Preview)\b", title, re.I):
        return False
    if len(title.split()) < 7:
        return False
    # Drop news-headline style: Title Case with no opinion words
    has_opinion = bool(re.search(
        r"\b(should|could|would|will|think|feel|believe|overrated|underrated|best|worst|"
        r"greatest|terrible|awful|amazing|incredible|better|worse|love|hate|"
        r"deserved|robbed|unfair|wrong|right|prove|showed|proved|means)\b",
        title, re.I,
    ))
    # Also allow longer titles that express any clear opinion structure
    return has_opinion or len(title.split()) >= 12


def fetch(endpoint: str, params: dict) -> list:
    try:
        r = requests.get(
            f"{BASE}/{endpoint}",
            headers=HEADERS,
            params=params,
            timeout=25,
        )
        r.raise_for_status()
        return r.json().get("data") or []
    except Exception as e:
        print(f"  Warning [{endpoint}]: {e}", file=sys.stderr)
        return []


def collect():
    seen: set[str] = set()
    rows: list[dict] = []

    def add(text: str, source: str) -> bool:
        text = text.strip()
        if not text or text in ("[deleted]", "[removed]"):
            return False
        key = text[:120]
        if key in seen:
            return False
        seen.add(key)
        label, notes = label_text(text)
        if label is None:
            return False
        rows.append({
            "text": text,
            "label": label,
            "notes": notes,
            "source": source,
            "ai_prelabel": label,
        })
        return True

    # 2022 World Cup window (Nov 20 – Dec 18 2022)
    wc22_a, wc22_b = 1668902400, 1671321600
    # 2018 World Cup window (Jun 14 – Jul 15 2018)
    wc18_a, wc18_b = 1528934400, 1531612800

    # ── Posts (self-posts with opinion titles) ────────────────────────────────
    print("Fetching posts…", file=sys.stderr)
    for params in [
        {"subreddit": "worldcup", "limit": 100, "after": wc22_a, "before": wc22_b, "sort": "desc"},
        {"subreddit": "worldcup", "limit": 100, "after": wc18_a, "before": wc18_b, "sort": "desc"},
        {"subreddit": "worldcup", "limit": 100, "sort": "desc"},
    ]:
        for p in fetch("posts/search", params):
            if p.get("stickied"):
                continue
            title    = (p.get("title") or "").strip()
            selftext = (p.get("selftext") or "").strip()
            if is_opinion_title(title):
                add(title, "post_title")
            if selftext not in ("", "[deleted]", "[removed]") and len(selftext.split()) >= 12:
                add(selftext[:700], "post_body")
        print(f"  posts batch – {len(rows)} total so far", file=sys.stderr)
        time.sleep(1.2)

    # ── General comments (multiple time windows) ───────────────────────────────
    print("Fetching general comments…", file=sys.stderr)
    for params in [
        {"subreddit": "worldcup", "limit": 100, "after": wc22_a,            "before": wc22_b, "sort": "desc"},
        {"subreddit": "worldcup", "limit": 100, "after": wc22_a + 86400*6,  "before": wc22_b, "sort": "desc"},
        {"subreddit": "worldcup", "limit": 100, "after": wc22_a + 86400*14, "before": wc22_b, "sort": "desc"},
        {"subreddit": "worldcup", "limit": 100, "after": wc18_a,            "before": wc18_b, "sort": "desc"},
        {"subreddit": "worldcup", "limit": 100, "after": wc18_a + 86400*7,  "before": wc18_b, "sort": "desc"},
        {"subreddit": "worldcup", "limit": 100, "sort": "desc"},
    ]:
        for c in fetch("comments/search", params):
            body = (c.get("body") or "").strip()
            if body and body not in ("[deleted]", "[removed]") and len(body.split()) >= 7:
                add(body[:600], "comment")
        print(f"  general comment batch – {len(rows)} total so far", file=sys.stderr)
        time.sleep(1.2)

    # ── Targeted keyword searches (body= param, no time window) ─────────────
    # Arctic Shift supports body= substring filter; combine with subreddit filter.
    # Use generous sleep to avoid 422 timeouts.
    print("Fetching targeted Reaction comments…", file=sys.stderr)
    for keyword in ["unbelievable", "robbery", "incredible", "what a goal",
                    "that referee", "can't believe", "what a save", "disgrace"]:
        for c in fetch("comments/search", {"subreddit": "worldcup", "body": keyword, "limit": 50}):
            body = (c.get("body") or "").strip()
            if body and body not in ("[deleted]", "[removed]") and len(body.split()) >= 4:
                add(body[:400], f"reaction_kw:{keyword}")
        time.sleep(3)
    print(f"  after Reaction keyword fetch – {len(rows)} total", file=sys.stderr)

    print("Fetching targeted Analysis comments…", file=sys.stderr)
    for keyword in ["tactical", "possession", "pressing", "because they", "due to",
                    "the reason", "historically", "dominated because", "formation"]:
        for c in fetch("comments/search", {"subreddit": "worldcup", "body": keyword, "limit": 50}):
            body = (c.get("body") or "").strip()
            if body and body not in ("[deleted]", "[removed]") and len(body.split()) >= 10:
                add(body[:600], f"analysis_kw:{keyword}")
        time.sleep(3)
    print(f"  after Analysis keyword fetch – {len(rows)} total", file=sys.stderr)

    return rows


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    rows = collect()

    counts: dict[str, int] = {}
    for r in rows:
        counts[r["label"]] = counts.get(r["label"], 0) + 1

    print(f"\nTotal examples : {len(rows)}", file=sys.stderr)
    print(f"Label counts   : {counts}", file=sys.stderr)

    # Warn if any label is underrepresented
    for label in ("Analysis", "Hot Take", "Reaction"):
        n = counts.get(label, 0)
        if n < 50:
            print(f"  WARNING: {label} has only {n} examples (<50)", file=sys.stderr)

    with open(OUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["text", "label", "notes", "source", "ai_prelabel"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Saved → {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()