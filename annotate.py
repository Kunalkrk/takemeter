"""
Full annotation pass over data.csv.
Applies the three-step decision hierarchy from planning.md Section 3 to every example.
Writes:
  - data.csv            (updated 'label' column)
  - edge_cases.txt      (running log of posts that gave genuine pause)
"""

import csv
import re
from pathlib import Path

DATA_PATH  = Path(__file__).parent / "data.csv"
EDGE_PATH  = Path(__file__).parent / "edge_cases.txt"

# ---------------------------------------------------------------------------
# Pattern library
# ---------------------------------------------------------------------------

# Strong causal connectives — the argument structure depends on them
CAUSAL_STRONG = re.compile(
    r"\b(because(?!\s+of\s+course|\s+why\b)|"       # because (not "because why" / "because of course")
    r"due to|result(?:ed|s) in|which means|"
    r"this is why|the reason (?:is|was|for|they|he|she)|"
    r"shows? that|therefore\b|thus\b|hence\b|"
    r"as a result|caused\b|that'?s why|which is why|"
    r"means that|allowed (?:them|him|her|the team)|"
    r"forced (?:them|him|her|the|their)|"
    r"contributed to|explains? why|"
    r"leading to|resulting in|"
    r"enabling (?:them|him|her|the))\b",
    re.I,
)

# Weaker causal language — context-dependent
CAUSAL_WEAK = re.compile(
    r"\b(since\s+\w+\s+\w|because of|in order to|so that)\b",
    re.I,
)

# Tactical / positional vocabulary
TACTICAL = re.compile(
    r"\b(possession|pressing|press(?:ed|ing)\b|formation\b|shape\b|"
    r"system\b|offside\b|high line|defensive block|counterattack|"
    r"counter.?press|half.?space|through ball|progressive pass|"
    r"xg\b|expected goal|wing.?back|false.?(?:nine|9)|inverted winger|"
    r"deep block|low block|high press|build.?up play|transition\b|"
    r"compactness|overload\b|"
    r"\d-\d-\d\b|\d-\d-\d-\d\b|"
    r"back (?:three|four|five|3|4|5)\b|"
    r"defensive (?:shape|line|block|third|structure|organization)|attacking third|"
    r"midfield (?:press|block|structure)|out of possession|"
    r"in possession|off the ball|on the ball|"
    # Additional common tactical expressions
    r"park(?:ing)? the bus|sit(?:ting)? (?:deep|back)\b|"
    r"high tempo\b|set pieces?\b|zonal marking\b|man.?marking\b|"
    r"time.?wasting\b|long ball\b|direct football\b|"
    r"overloading\b|underlapping\b|press triggers?\b|"
    r"defensive (?:midfielder|midfield)\b|"
    r"holding midfielder\b|box.?to.?box\b|"
    r"playing out from the back\b|third man runs?\b|"
    r"defensive duties\b|positional play\b)\b",
    re.I,
)

# Specific factual claims: statistics and historical evidence
STATS = re.compile(
    # Standard: number + soccer unit
    r"\b\d+[\.,]?\d*\s*(?:goal|shot|save|pass|assist|touch|minute|cap|clean sheet|km|%|km/h|xg)\b|"
    # Bare integer + common soccer nouns (catches "fouled 24 times", "3 corners", "5 fouls")
    r"\b\d+\s+(?:times\b|fouls?\b|cards?\b|corners?\b|chances?\b|shots?\b|blocks?\b|"
    r"clearances?\b|interceptions?\b|crosses?\b|offsides?\b|penalties?\b)\b|"
    # Win/draw/loss records like "1-1-1", "went 2-0-1"
    r"\b\d-\d-\d\b|"
    # Historical references
    r"\b(?:in|since)\s+(?:19|20)\d{2}\b|"
    # Prefixed counts
    r"\b(?:only|just|more than|at least|fewer than|never|always)\s+\d+\s+"
    r"(?:time|year|game|match|tournament|world cup)\b|"
    # Records and rankings
    r"\bworld cup record\b|\bfifa ranking\b|"
    r"\b(?:first|second|third)\s+(?:in|of)\s+(?:the\s+)?(?:world|europe|group|tournament)\b|"
    # Pass completion, shots on target percentages mentioned in context
    r"\b\d+\s*(?:of|out of)\s*\d+\b",
    re.I,
)

# Performance evaluation language (required for conversational analysis path)
EVAL = re.compile(
    r"\b(?:won\b|lost\b|played (?:well|poorly|badly|brilliantly|terribly|great)|"
    r"performed\b|dominated\b|struggled\b|failed\b|succeeded\b|"
    r"proved\b|better\b|worse\b|stronger\b|weaker\b|"
    r"effective\b|ineffective\b|excellent\b|disappointing\b|"
    r"outplayed\b|outclassed\b|underperformed\b|overperformed\b|"
    r"solid\b|shaky\b|clinical\b|wasteful\b|inconsistent\b|dominant\b|"
    r"defend(?:ing|ed|s)\b|attack(?:ing|ed|s)\b|control(?:led|ling|s)\b|"
    r"dictate[ds]?\b|overran\b|pressing well|defending well)\b",
    re.I,
)

# Soccer-specific emotional reactions — NOT generic spam enthusiasm
REACTION_EXPR = re.compile(
    r"\b(?:omg|wtf|omfg|lmao|lmfao|holy\s+(?:shit|cow|moly)|"
    r"unbelievable\b|incredible\b|insane\b|"
    r"no way\b|are you kidding|"
    r"what a (?:goal|save|miss|tackle|foul|game|match|half|performance)|"
    r"i (?:still |just )?can'?t (?:believe|even)|"
    r"that (?:ref(?:eree)?|var|call|decision|penalty|foul)|"
    r"robbery\b|robbed\b|rigged\b|disgrace\b|scandal\b|outrageous\b|"
    r"(?:yess+|nooo+|bruh)\b|"
    r"GOOOAL|this is (?:insane|crazy|unreal)|what just happened|"
    r"(?:that was|this was)\s+(?:horrible|terrible|awful|a (?:joke|disgrace|travesty))|"
    r"stunned\b|speechless\b|jaw.?drop|heart.?breaking|"
    r"disgusting\b|shocking\b)\b",
    re.I,
)

# Noise — logistics, spam, meta-posts (return None)
NOISE = re.compile(
    r"\b(?:ticket|streaming|iptv|subscription|t.shirt|jersey|for sale|selling\b|"
    r"hotel|fan.?fest|best gift|watching online|how do i|where can i|"
    r"anyone know where|looking to buy)\b",
    re.I,
)

# ---------------------------------------------------------------------------
# Core decision function
# ---------------------------------------------------------------------------

def decide(text: str) -> tuple[str, str, str]:
    """
    Returns (label, confidence, edge_note).
    confidence: 'clear' | 'borderline'
    edge_note: non-empty string if this was a hard case
    """
    t = text.strip()
    words = t.split()
    n = len(words)
    tl = t.lower()

    # Pre-filter noise and trivially short posts
    if n < 6:
        return "Hot Take", "clear", ""
    if NOISE.search(tl):
        return "Hot Take", "clear", ""   # noise → not useful, dump in Hot Take

    # Signal extraction
    cs         = bool(CAUSAL_STRONG.search(tl))   # strong causal
    cw         = bool(CAUSAL_WEAK.search(tl))      # weak causal
    causal     = cs or cw
    tactical   = bool(TACTICAL.search(tl))
    stats      = bool(STATS.search(tl))
    evaluation = bool(EVAL.search(tl))
    emotional  = bool(REACTION_EXPR.search(t))

    fact_count   = int(tactical) + int(stats)
    exclamations = t.count("!")
    caps_words   = sum(1 for w in words if w.isupper() and len(w) > 2)

    # ── STEP 1: Analysis ──────────────────────────────────────────────────────
    # Evidence must be LOAD-BEARING — the argument cannot stand without it.
    # Strong path: causal connective + specific evidence, OR two types of evidence
    strong = n >= 15 and (
        (cs and fact_count >= 1) or
        (fact_count >= 2) or
        (tactical and cs and n >= 20)
    )

    # Conversational path: reasoning without hard stats
    # Requires strong causal + performance evaluation + substance (25+ words) + no pure emotion
    conversational = n >= 25 and cs and evaluation and not emotional

    is_analysis = strong or conversational

    # Single stat without causal chain → Hot Take (decision rule from planning.md)
    single_stat_only = stats and not tactical and not causal
    if single_stat_only:
        is_analysis = False

    # ── STEP 2: Reaction ──────────────────────────────────────────────────────
    # Primarily expressing a feeling about a specific event, not constructing an argument.
    is_reaction = not is_analysis and (
        (emotional and n <= 50) or
        (exclamations >= 2 and caps_words >= 1 and n <= 25) or
        (exclamations >= 3 and n <= 30)
    )

    # ── Confidence + edge case notes ─────────────────────────────────────────
    note = ""
    confidence = "clear"

    if is_analysis:
        if not strong and conversational:
            confidence = "borderline"
            note = (
                f"BORDERLINE Analysis/Hot Take — conversational reasoning without hard stats. "
                f"Causal: yes. Evaluation language: yes. "
                f"Decision: Analysis because causal chain + performance eval are load-bearing."
            )
        elif single_stat_only:
            # Shouldn't reach here, but guard anyway
            confidence = "borderline"
            note = "Single stat — would normally be Hot Take, but other analysis signals present."
    elif is_reaction:
        if emotional and n > 30:
            confidence = "borderline"
            note = (
                f"BORDERLINE Reaction/Hot Take — emotional language in a {n}-word post. "
                f"Decision: Reaction because emotional expression is the primary purpose."
            )
        if n <= 50 and emotional and stats:
            confidence = "borderline"
            note = (
                "BORDERLINE Reaction/Analysis — emotional post with a stat. "
                "Decision: Reaction because stat is not load-bearing; expression of feeling is the point."
            )
    else:
        # Hot Take
        if causal and not stats and not tactical and n >= 20:
            confidence = "borderline"
            note = (
                "BORDERLINE Hot Take/Analysis — has causal language but no specific evidence. "
                "Decision: Hot Take because 'if you remove the causal phrase, the claim still stands.'"
            )
        elif emotional and n > 50:
            note = (
                "Long emotional post with no argument → Hot Take. "
                "Reaction ruled out because it exceeds 50 words without a primary event reaction."
            )

    if is_analysis:
        return "Analysis", confidence, note
    if is_reaction:
        return "Reaction", confidence, note
    return "Hot Take", confidence, note

# ---------------------------------------------------------------------------
# Run annotation
# ---------------------------------------------------------------------------

rows = list(csv.DictReader(open(DATA_PATH, encoding="utf-8")))

counts        = {"Analysis": 0, "Hot Take": 0, "Reaction": 0}
changed       = 0
edge_cases    = []
borderline_n  = 0

for i, row in enumerate(rows):
    old_label = row["label"]
    new_label, confidence, note = decide(row["text"])
    row["label"] = new_label
    counts[new_label] += 1
    if new_label != old_label:
        changed += 1
    if note:
        borderline_n += 1
        edge_cases.append({
            "id": i,
            "text": row["text"][:300],
            "old_label": old_label,
            "new_label": new_label,
            "confidence": confidence,
            "note": note,
        })

# Write updated CSV
with open(DATA_PATH, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["text", "label", "notes", "source", "ai_prelabel"])
    writer.writeheader()
    writer.writerows(rows)

# Write edge cases log
with open(EDGE_PATH, "w", encoding="utf-8") as f:
    f.write(f"EDGE CASES LOG — {borderline_n} borderline decisions out of {len(rows)} examples\n")
    f.write("=" * 80 + "\n\n")
    for ec in edge_cases:
        f.write(f"[{ec['id']}] {ec['old_label']} → {ec['new_label']}  ({ec['confidence']})\n")
        f.write(f"NOTE: {ec['note']}\n")
        f.write(f"TEXT: {ec['text']}\n")
        f.write("-" * 60 + "\n\n")

print(f"Total examples  : {len(rows)}")
print(f"Labels changed  : {changed}")
print(f"Borderline cases: {borderline_n}")
print(f"Distribution    : {counts}")
total = sum(counts.values())
for k, v in sorted(counts.items(), key=lambda x: -x[1]):
    pct = v / total * 100
    flag = " ← IMBALANCE" if pct > 70 else ""
    print(f"  {k:12s}: {v:5d}  ({pct:.1f}%){flag}")
print(f"\nEdge cases written → {EDGE_PATH}")