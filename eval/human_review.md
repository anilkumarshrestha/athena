# Eval B — native-speaker review of generated stories

Each story checked by a native Nepali reader for grammar, idiom and child-appropriateness.
Cause column: **constraint** = the correct word was blocked by the learner's mastery set;
**model** = the correct word was allowed, the model got it wrong; **style** = acceptable but unnatural.

| # | Date | Learner / preset | Verdict | Issues |
|---|---|---|---|---|
| 1 | 2026-10-17 | ram / `ne_mid` | ❌ fail (grammar) | see below |

## 1 — ram / ne_mid

```
आज पानी आयो।
राम सानो झोला लियो।
राम नयाँ बाटो गयो।
पानीमा राम खुसी भयो।
```

| Wrong | Correct | Cause | Note |
|---|---|---|---|
| पानी आयो | पानी पर्यो | **constraint** | पर्यो needs conjunct र्य (not mastered); model swapped in a wrong verb instead of rephrasing |
| राम … लियो | रामले … लियो | **model** | ergative -ले missing on transitive past verb; रामले was allowed |
| राम खुसी भयो | राम रमायो | style | रमायो was allowed; minor |

**Action taken:** writer prompt now states the ergative rule, collocations, and "rephrase, never
substitute an unnatural word" (athena/agents/writer.py). Re-review after the change.
