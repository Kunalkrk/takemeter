# TakeMeter — Fine-Tuning Project Report

This report summarizes the process of fine-tuning a text classifier to categorize social media posts and compares its performance against a zero-shot baseline using the Groq API.

## 1. Project Overview

The goal of this project was to build a text classification system capable of distinguishing between **Analysis**, **Hot Take**, and **Reaction** posts from r/worldcup, a Reddit community for World Cup soccer discussion. A DistilBERT model was fine-tuned on a custom labeled dataset of 1,264 examples, and its performance was benchmarked against a zero-shot classifier powered by Groq's `llama-3.1-8b-instant` model.

---

## 2. Evaluation Results

### Overall Accuracy

| Model                         | Accuracy |
| :---------------------------- | :------- |
| Zero-shot baseline (Groq)     | 0.347    |
| Fine-tuned DistilBERT         | 0.753    |

Fine-tuning resulted in a significant improvement of **0.405** in accuracy over the zero-shot baseline.

### Per-Class Metrics

#### Fine-Tuned DistilBERT

```
              precision    recall  f1-score   support

    Analysis       0.65      0.45      0.53        29
    Hot Take       0.78      0.91      0.84       133
    Reaction       0.64      0.32      0.43        28

    accuracy                           0.75       190
   macro avg       0.69      0.56      0.60       190
weighted avg       0.74      0.75      0.73       190
```

#### Zero-Shot Baseline (Groq — llama-3.1-8b-instant)

```
              precision    recall  f1-score   support

    Analysis       0.30      0.72      0.42        29
    Hot Take       0.79      0.17      0.27       133
    Reaction       0.25      0.82      0.38        28

    accuracy                           0.35       190
   macro avg       0.45      0.57      0.36       190
weighted avg       0.63      0.35      0.31       190
```

### Confusion Matrix (Fine-Tuned Model)

| True \ Predicted | Analysis | Hot Take | Reaction |
| :--------------- | :------- | :------- | :------- |
| Analysis         | 13       | 16       | 0        |
| Hot Take         | 7        | 121      | 5        |
| Reaction         | 0        | 19       | 9        |

### Pass/Fail Against Success Criteria

From planning.md Section 6, the model passes only if all four conditions are met on the held-out test set (190 examples, 25+ per class).

| Condition       | Threshold | Result | Pass/Fail |
| :-------------- | :-------- | :----- | :-------- |
| Macro F1        | ≥ 0.78    | 0.60   | FAIL      |
| Analysis F1     | ≥ 0.65    | 0.53   | FAIL      |
| Hot Take F1     | ≥ 0.65    | 0.84   | PASS      |
| Reaction F1     | ≥ 0.65    | 0.43   | FAIL      |

**Overall verdict: FAIL.** The model clears the threshold on Hot Take but falls short on Analysis and Reaction. The macro F1 of 0.60 is well above the majority-class baseline of ~0.22 but does not reach the 0.78 target. The primary failure mode is low recall on Analysis (0.45) and Reaction (0.32) — the model over-predicts Hot Take, which accounts for 70% of the training data.

---

## 3. Analysis of Misclassified Examples

### Example 1

**Text:** Like Hitler giving medals in 36. I am an American and he is an utter disgrace as a president and worse as a human being.  
**True Label:** Reaction  
**Predicted Label:** Hot Take (confidence: 0.64)

- **Labels confused:** Reaction → Hot Take
- **Why the boundary is hard:** The post expresses strong negative emotion, which fits Reaction. But the confrontational, opinionated tone and implicit claim about a public figure read like a Hot Take. The model likely weighted the strong opinion over the event-driven emotional response.
- **Labeling/data issue:** Highlights the ambiguity between "emotional response to an event" (Reaction) and "strong controversial opinion" (Hot Take) for highly charged statements not tied to a specific match moment.
- **Fix:** Add more training examples that clearly distinguish event-driven emotional responses from sustained opinions. Emphasizing the *immediacy* and *event-specificity* of Reaction in the label definition would help.

### Example 2

**Text:** No way around it, unless matches get played at the same time. But that eats into viewership advertising revenue, so it's not too viable. However, there is no historic trend that shows that the team ...  
**True Label:** Analysis  
**Predicted Label:** Hot Take (confidence: 0.55)

- **Labels confused:** Analysis → Hot Take
- **Why the boundary is hard:** The post opens with a strong assertion ("No way around it") which reads like a Hot Take opener. The subsequent reasoning about revenue and historical trends is analytical, but the model appears to weight the opening sentence heavily.
- **Labeling/data issue:** Training examples in the Analysis class may skew toward neutral or clearly investigative openings, leaving the model poorly calibrated for analytical posts that begin with a bold claim before presenting evidence.
- **Fix:** Include more Analysis examples that lead with a strong premise and then support it with reasoning. This teaches the model to evaluate the full post rather than anchoring on the opening tone.

### Example 3

**Text:** 80% possession usually means you are turning down chances to attack in order to keep up the safe passing. Its never that high when teams are genuinely trying to attack rather than play it safe all the...  
**True Label:** Hot Take  
**Predicted Label:** Analysis (confidence: 0.53)

- **Labels confused:** Hot Take → Analysis
- **Why the boundary is hard:** The post uses tactical vocabulary ("possession", "attack") and frames its claim as a general observation ("usually means"), which reads as explanatory. But it makes a broad generalization without citing specific evidence or data to support it — the stat (80%) is illustrative, not load-bearing.
- **Labeling/data issue:** The model appears to conflate confident, jargon-heavy language with analytical depth. A Hot Take that sounds authoritative and uses soccer terminology can look like Analysis on the surface without any actual evidence.
- **Fix:** Add more Hot Take examples that use tactical vocabulary confidently but lack a causal chain or specific evidence. The model needs examples that demonstrate the difference between *sounding* analytical and *being* analytical.

### 3.1 Sample Classifications

Here are some example posts classified by the fine-tuned model, including both correct and misclassified predictions:

| # | Text (truncated) | True Label | Predicted Label | Confidence |
| :-- | :---------------- | :---------- | :--------------- | :---------- |
| 1 | Like Hitler giving medals in 36. I am an American and he is an utter disgrace as a president and worse as a human being. | Reaction | Hot Take | 0.64 |
| 2 | No way around it, unless matches get played at the same time. But that eats into viewership advertising revenue, so it's not too viable. However, there is no historic trend that shows that the team ... | Analysis | Hot Take | 0.55 |
| 3 | delete your disgraceful post. we're talking about soccer, not politics. | Hot Take | Hot Take | 0.74 |
| 4 | Except for this world cup where due to the heat they actually stop the game for water breaks so the players can hydrate themselves. Plus the medical staff can check to see if anyone has heat stroke. I don't see any other sport doing that. | Analysis | Analysis | 0.50 |
| 5 | Wow what a goal! | Reaction | Reaction | 0.82 |

**Explanation for correctly predicted example #5:** The post "Wow what a goal!" is a quintessential Reaction as it expresses an immediate emotional response to a match event, which the model correctly identified with high confidence.

---

## 5. Reflection: Model's Understanding vs. Intent

While the fine-tuned DistilBERT model demonstrated a significant improvement in accuracy over the zero-shot baseline, a deeper look at its performance, particularly the misclassifications, reveals some gaps between the intended label definitions and what the model's decision boundaries actually captured.

### What the Model Captured Well

The model was generally effective at identifying clear-cut examples of Hot Take and Reaction posts. Posts with obvious emotional exclamations (e.g., "Wow what a goal!") were confidently classified as Reaction. Similarly, posts presenting strong, often controversial opinions without substantial backing (e.g., "delete your disgraceful post...") were often correctly identified as Hot Take. It also showed a reasonable ability to classify Analysis when posts contained explicit evidence, statistics, or structured reasoning, especially when the tone was more neutral or academic.

### What the Model Overfit To or Missed

1. **Overfitting to tone and intensity:** The most prominent observation is the model's tendency to sometimes overfit to the *intensity* or *assertiveness* of a statement rather than its underlying content or rhetorical structure. Highly emotional or very confidently stated posts, even if they were reactions or contained some analytical elements, were often pushed towards Hot Take. This explains why many Reaction posts with strong negative emotions were misclassified as Hot Take (e.g., Example 1: "Like Hitler giving medals..."). The model seemed to prioritize the strong, confrontational tone typical of hot takes over the immediate, event-driven nature of a reaction.

2. **Missing subtle analytical cues:** Conversely, for Analysis, the model sometimes struggled when analytical content was embedded within more opinionated language or when the supporting evidence was implicit. If an Analysis post began with a strong stance or used less formal language, the model might default to Hot Take (e.g., Example 2: "No way around it..."). This suggests it might be missing more subtle rhetorical cues that signal analytical depth, particularly when they don't conform to a strictly academic or objective style.

3. **Ambiguity in label definitions:** The confusion between Reaction and Hot Take, and Hot Take and Analysis, highlights an inherent ambiguity in the label definitions themselves, which the model then struggled to disambiguate. The model learned the *patterns* present in the training data, but those patterns do not always align with the subtle nuances of human intention behind the label definitions. A Hot Take that is well-argued (even if based on a flawed premise) can resemble an Analysis, and a passionate Reaction can sound like a Hot Take due to its intensity.

4. **Short and ambiguous posts:** Very short posts or those with highly ambiguous language were challenging. In such cases, the model likely defaulted to the most frequent class in the dataset (Hot Take), or its confidence in any prediction was low.

### Conclusion

While fine-tuning greatly improved the classifier's performance, the model is still learning to navigate the nuanced and often overlapping definitions of Analysis, Hot Take, and Reaction in informal text. Future improvements could focus on refining label definitions to reduce ambiguity, providing more diverse training examples at the challenging class boundaries, and potentially exploring more sophisticated models capable of understanding rhetorical intent beyond surface-level sentiment or assertiveness.

---

## 4. AI Usage Disclosure

Claude (claude-sonnet-4-6) was used at three stages of this project, as specified in planning.md Section 7:

1. **Label stress-testing:** Before annotation, Claude generated boundary cases between Analysis and Hot Take to verify the decision hierarchy was unambiguous. Any case that could not be classified in under 10 seconds triggered a definition revision.

2. **Annotation assistance:** Each example was pre-labeled by the rule-based `annotate.py` script, which implements the three-step decision hierarchy from planning.md. The `ai_prelabel` column in data.csv records the automated label alongside the final label. All labels were reviewed against the decision rules; 190 borderline cases were logged in `edge_cases.txt`.

3. **Failure analysis assistance:** Claude assisted in identifying patterns in misclassified examples after evaluation. All patterns were verified manually against multiple independent examples before inclusion in this report. Patterns supported by fewer than three examples are treated as speculative.