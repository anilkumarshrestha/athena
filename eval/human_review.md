# Eval B — native-speaker review of generated stories

Each story checked by a native Nepali reader for grammar, idiom and child-appropriateness.
Cause column: **constraint** = the correct word was blocked by the learner's mastery set;
**model** = the correct word was allowed, the model got it wrong; **style** = acceptable but unnatural.

| # | Date | Learner / preset | Verdict | Issues |
|---|---|---|---|---|
| 1 | 2026-10-17 | ram / `ne_mid` | ❌ fail (grammar) | see below |
| 2 | 2026-10-17 | sita / `ne_basic` | ❌ fail (nonsense) | word-list fallback shown as a sentence; see below |
| 3 | 2026-10-17 | (rule) | — | honorific verbs for elders; see below |

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

## 2 — sita / ne_basic

```
आमा र भात
अंगुर अचार अनि आए आगो आज आमा आयो आलु इनार उनको उनी
```

Not a story: the last-resort fallback (first 12 readable words, alphabetical) displayed as a sentence.

**Cause:** one writer call took 31.6s against a 20s budget (HTTP timeout only fires on a silent
connection), so no retry was possible; only one sentence of the draft verified.

**Actions:** budget now enforced with a hard deadline on the writer call; new **template**
fallback builds short grammatical sentences from readable words ("खेतमा कुखुरा छ।",
"भात तातो छ।"), all verified; the word list remains only as a last resort and is rendered as
separate practice words, not a sentence. Template output needs native review.

**Follow-up (native review of template output):** "मह तातो छ" and "आमाको बल" are grammatical but
not things people say. Templates now use natural pairings instead of free cross-products: each
noun lists only what is commonly said about it (मह मीठो; भात तातो/मीठो), and possessions fit the
owner (दिदीको बल, आमाको छाता). Maps live in athena/fallback.py.

## 3 — rule: respect for elders

Elders and older siblings (आमा, बुबा, हजुरआमा, काका, गुरु, दाइ, दिदी …) always take honorific
verbs: "आमा आउनुभयो", "दाइले खाना खानुभयो" — never "आमा आयो", "दाइले खायो". Child, younger
siblings and animals take plain forms.

**Actions:** writer prompt states the rule with examples; templates add honorific elder sentences
("आमा खेत जानुभयो", "हजुरआमा घरमा हुनुहुन्छ"); test asserts no elder sentence ends in a plain verb.
