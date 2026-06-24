# Classification Project Planning

## 1. Community

**Chosen community:** r/worldcup (Reddit)

The r/worldcup subreddit is a large, active forum where soccer fans discuss World Cup matches, players, teams, tactics, and tournament storylines. It draws a global audience across skill levels — from casual fans reacting emotionally in real time to tactically knowledgeable followers breaking down formations and statistics.

This community is a strong fit for a classification task for three reasons. First, the discourse is structurally varied: the same event (say, a controversial penalty) will produce emotional reactions ("THIS REF IS A JOKE"), hot takes ("Brazil are frauds"), and analytical posts ("The penalty was correct — the defender's arm was in an unnatural position based on FIFA's 2022 guidance") all within minutes of each other. Second, the community has a well-defined topic domain (international soccer), which constrains vocabulary and makes label boundaries more meaningful than in a general-purpose forum. Third, the signal-to-noise ratio is high enough that most posts have a clear primary intent, while a meaningful fraction sit near label boundaries — making the task genuinely interesting without being intractable.

---

## 2. Labels

### Label 1: Analysis

A post that supports its opinion with specific evidence such as tactics, statistics, historical comparisons, or detailed reasoning that explains *why* the conclusion follows.

**Example posts:**
- "Argentina dominated the second half because they switched to a more aggressive press and forced France into turnovers in midfield — Messi had six progressive carries in the final 30 minutes alone."
- "Japan's defensive shape stayed compact all game, allowing them to limit Germany to low-quality chances despite having less possession; their back-five compressed the half-spaces brilliantly."

---

### Label 2: Hot Take

A post expressing a strong or controversial opinion with little or no meaningful supporting evidence — the claim is the point, not the reasoning behind it.

**Example posts:**
- "Mbappé is already the greatest World Cup player of all time."
- "Brazil would lose to any decent European team right now."

---

### Label 3: Reaction

A post whose primary purpose is expressing an immediate emotional response to a match event, player moment, referee decision, or tournament development, rather than making or supporting an argument.

**Example posts:**
- "WHAT A GOAL!! I can't believe he scored from there!"
- "That referee was absolutely terrible today."

---

## 3. Hard Edge Cases

**The most genuinely ambiguous boundary is between Analysis and Hot Take** when a post includes exactly one statistic or one factual claim in service of a broad opinion.

Example: *"England are overrated — they've only beaten one top-10 FIFA team in the last two years."*

This post has a statistic, but the statistic is a single data point that supports a sweeping claim without explaining mechanism, context, or causation. It *looks* like analysis but functions like a hot take dressed in one number.

A second hard boundary is **Reaction vs. Analysis** for posts that name a specific event and assert an impact: *"That penalty call completely changed the game."* This could be a pure emotional reaction or the opening sentence of an analytical argument.

**Handling strategy:**

Apply a decision hierarchy in order:

1. Does the post contain at least two pieces of evidence *and* explain how they connect to the conclusion? → **Analysis**
2. Is the post's dominant register emotional or exclamatory, with no argument being constructed? → **Reaction**
3. Otherwise → **Hot Take**

For the Analysis/Hot Take edge: the test is whether the evidence is *load-bearing*. If removing the statistic would leave no argument at all, the post is a Hot Take. If the reasoning depends on the evidence to hold together, it is Analysis.

For borderline cases during annotation, a secondary annotator reviews the post and the majority label is used. Cases where two annotators disagree after discussion are flagged, added to an "ambiguous" pool, and used to refine the decision rules rather than discarded.

---

## 4. Data Collection Plan

**Sources:** Reddit posts and top-level comments collected via the Arctic Shift public archive API (`arctic-shift.photon-reddit.com/api`), which provides unauthenticated access to Reddit post and comment history. Three subreddits were used:

| Subreddit | Role | What was collected |
|-----------|------|--------------------|
| r/worldcup | Primary | Posts and comments from the 2022 WC window (Nov 20 – Dec 18 2022) and 2018 WC window (Jun 14 – Jul 15 2018), plus general batches and targeted keyword searches |
| r/soccer | Supplementary (Analysis) | Tactical comments fetched to address Analysis class underrepresentation |
| r/football | Supplementary (Analysis) | Tactical comments fetched in a second rebalancing round for the same reason |

**Final volume:** 1,264 examples total.

| Label | Count | % |
|-------|-------|---|
| Hot Take | 880 | 69.6% |
| Analysis | 194 | 15.3% |
| Reaction | 190 | 15.0% |

**Collection strategy:**

The primary collection used time-windowed batches from r/worldcup for both the 2022 and 2018 tournaments, plus targeted single-keyword searches using the `body=` parameter for Reaction vocabulary ("unbelievable", "robbery", "what a goal") and Analysis vocabulary ("tactical", "possession", "pressing", "formation"). Multi-word phrases and time-windowed keyword searches caused server timeouts (422), so keyword searches were run without time constraints.

Hot Take was the dominant natural register of the subreddit. Analysis was underrepresented after the first collection pass (~3% of examples), requiring two supplementary rounds from r/soccer and r/football tactical discussion threads. The `source` column in data.csv records the subreddit and triggering keyword for every example.

Do not use synthetic data or paraphrasing to pad a label — it would distort the natural language distribution the classifier is meant to learn.

---

## 5. Evaluation Metrics

**Primary metric: Macro-averaged F1**

Macro F1 averages the F1 score for each label independently and treats them equally regardless of class frequency. This is the right primary metric because the labels are not equally distributed in the wild — Reaction posts naturally outnumber Analysis posts — and a classifier that ignores the rarer Analysis label should not score well. Accuracy would reward a lazy majority-class predictor; macro F1 penalizes it.

**Secondary metric: Per-class F1 (reported separately)**

Macro F1 hides which label is driving errors. Reporting F1 per label reveals whether the model struggles on the Analysis/Hot Take boundary specifically, which is the hardest distinction and the most consequential one for community moderation use. A model that is strong on Reaction but weak on Analysis is a different failure mode than one that confuses Hot Take with Analysis.

**Tertiary metric: Confusion matrix**

The confusion matrix surfaces which pairs of labels are most commonly swapped. Given the design of the task, we expect the most errors to appear between Analysis and Hot Take (evidence-lite posts) and between Reaction and Hot Take (emotional assertions). Tracking this directly guides future data collection and rule refinement.

**Why not just accuracy?**

With three labels and a realistic class imbalance of roughly 50/30/20, a classifier that always predicts Reaction would achieve ~50% accuracy and a Macro F1 of approximately 0.22 — since F1 for the two ignored classes would be 0. That baseline makes the target threshold in Section 6 meaningful rather than arbitrary.

---

## 6. Definition of Success

**Single pass/fail criterion:** The classifier passes if it meets *all three* of the following conditions on a held-out test set of at least 75 labeled examples, with a minimum of 25 examples per class:

| Condition | Threshold |
|-----------|-----------|
| Macro F1 | ≥ 0.78 |
| Analysis F1 | ≥ 0.65 |
| Hot Take F1 | ≥ 0.65 |
| Reaction F1 | ≥ 0.65 |

The test set is held out before any training begins, drawn from the same r/worldcup source as the training data, and annotated using the same label definitions. The 75-example minimum (25 per class) ensures per-class estimates are stable enough to be meaningful; with fewer examples, a single misclassification swings F1 by more than the margin between pass and fail.

**Why 0.78?** A majority-class baseline (always predict Reaction) yields Macro F1 ≈ 0.22 on the expected 50/30/20 distribution. A threshold of 0.78 requires the model to perform substantially above that baseline across all three labels simultaneously. A model scoring below 0.70 would produce enough misclassifications to undermine user trust in a live moderation tool; a model above 0.85 would be considered strong.

**What the per-class floor catches:** A model could hit Macro F1 ≥ 0.78 by excelling on Reaction (the majority class) while scoring 0.55 on Analysis. The 0.65 floor on every class prevents that failure mode — if any single label falls below it, the model does not pass regardless of the macro number.

---

## 7. AI Tool Plan

### Label Stress-Testing

Before annotation begins, Claude will be given the three label definitions and the edge case decision hierarchy from Section 3 and asked to generate 10 posts that sit at the boundary between Analysis and Hot Take, and 5 posts that sit at the boundary between Reaction and Analysis. The prompt will be explicit: *"Generate posts a human annotator would struggle to classify — where the post has surface features of one label but the underlying intent fits another."*

Each generated post will be classified independently before checking what Claude intended. Any post that cannot be assigned a label confidently, or where the decision rule from Section 3 does not resolve the ambiguity cleanly, is a signal that the definition needs tightening. The specific failure will be used to rewrite either the definition sentence or the decision hierarchy before annotation starts. This step is a gate — annotation does not begin until every stress-test post can be classified in under 10 seconds without consulting notes.

### Annotation Assistance

Claude will be used to pre-label examples before human review. The workflow is:

1. Collect a batch of raw posts from r/worldcup.
2. Send each post to Claude with the full label definitions and decision hierarchy as a system prompt, asking for a single label and a one-sentence justification.
3. Review every pre-labeled example — the human label is always final.
4. Track pre-labeled examples in a dedicated column (`ai_prelabel`) in the annotation spreadsheet, recording Claude's label alongside the final human label. This column is never deleted; it becomes the basis for measuring agreement rate between Claude and the human annotator.

The `ai_prelabel` column will be disclosed in the project's AI Usage section. Examples where Claude's label and the human label disagree are treated as a secondary source of hard edge cases and reviewed first — disagreements often surface definition gaps faster than random sampling does.

### Failure Analysis

After evaluation, the full list of misclassified test examples — the model's prediction, the true label, and the post text — will be passed to Claude with the prompt: *"Identify patterns in these misclassifications. Group them by the type of error and describe what surface feature of the post likely caused the wrong prediction."*

The output will be treated as a hypothesis list, not a conclusion. Each pattern Claude identifies will be verified manually by reading the examples it cites and checking whether the grouping holds on examples it did not cite. Patterns that appear in at least three independent examples and survive manual spot-checking will be reported in the evaluation writeup. Patterns supported by only one or two examples will be noted as speculative. This prevents the failure analysis from overfitting to Claude's framing of the errors rather than the actual structure of the mistakes.
