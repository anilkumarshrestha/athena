# Athena — DESIGN.md

The visual system for Athena. **Every UI change follows this file.** If a screen
needs something not defined here, add it here first, then use it.

Two surfaces, one token set:

- **Child surface** — story, read-aloud, feedback. A picture book. Big type,
  almost no chrome, bright sky paper, playful colors.
- **Adult surface** — teacher grid, verifier log, eval charts, printable pack.
  A calm instrument panel. Dense, precise, quiet.

Both sit on the same light sky background and share all semantic colors. They
differ in type size, density and font.

Light mode only. Classroom tablets in daylight; the printable pack is paper.
No dark theme for the demo.

---

## 1. Principles

1. **Content is the hero.** The story and its illustration own the child
   screen. UI chrome is a guest.
2. **Meaning before decoration, except the child accents.** Outcome, mastery
   and interactive colors always mean something. On the child surface only,
   four accents (`sun` yellow, `coral` red, `leaf` green, `sky` blue) may
   decorate avatars, tiles and button edges. They never carry state.
3. **Never color alone.** Every semantic state also differs by shape, fill or
   line style, so it survives colorblindness and black-and-white printing.
4. **Devanagari is first-class.** Every font choice must render conjuncts
   (क्ष त्र ज्ञ श्र) cleanly at both 14px and 48px. Test with real words.
5. **Show the machine honestly.** The verifier log and eval views look like
   instruments: monospace, aligned, no marketing gloss.

---

## 2. Color

All values are WCAG-checked against `paper` (#EAF6FF). Ratios in brackets.

### Neutrals (cool sky)

| Token | Hex | Use |
|---|---|---|
| `paper` | `#EAF6FF` | Page background, both surfaces |
| `paper-sunken` | `#D9EDFB` | Wells, table header rows, code/log background |
| `card` | `#FFFFFF` | Raised surfaces: story card, panels |
| `line` | `#CFE3F2` | Default 1px borders, dividers |
| `line-strong` | `#8FB4D0` | Input borders, unseen-unit outlines, focus-adjacent |
| `ink` | `#1E2A4A` | Primary text, story text (13:1) |
| `ink-2` | `#3A4A6B` | Secondary text, labels (8:1) |
| `ink-3` | `#55658A` | Tertiary text, captions, axis labels (5:1) |
| `ink-4` | `#9AA8C2` | Disabled, placeholder, decorative only — **never body text** (2.5:1) |

Never use pure black `#000` as a text color. `card` is white `#FFFFFF`.

### Interactive

| Token | Hex | Use |
|---|---|---|
| `primary` | `#1D6FE8` | Buttons, links, focus ring, selected state (4.6:1) |
| `primary-hover` | `#1558BD` | Hover / pressed |
| `primary-soft` | `#D9E8FF` | Selected row, active tab background |
| `on-primary` | `#FFFFFF` | Text on primary |

`primary` is **only** for things you can press or things that are selected.
It is never used for headings, illustrations or decoration.

### Child accents (child surface decoration only)

| Token | Fill | Edge (3D bottom border) | Soft |
|---|---|---|---|
| `sun` | `#FFC800` | `#D19F00` | `#FFF3BF` |
| `coral` | `#FF5A5F` | `#D13B40` | `#FFE3E3` |
| `leaf` | `#3DBB4F` | `#2A9239` | `#DDF6E0` |
| `sky` | `#38A8FF` | `#1C86D6` | `#D6EEFF` |

Text on `sun` uses `on-sun` `#4A3600`; text on the others is `ink` or `soft`
backgrounds. Chunky buttons: fill + `border-b-4` in the edge color; pressed =
`translate-y-1` and `border-b-0`. Cycle accents across learner tiles by index.
Never use an accent to signal state.

### Brand

| Token | Hex | Use |
|---|---|---|
| `crimson` | `#C8102E` | Logo mark only. Nowhere else — red-family colors mean "error" in this app |

### Reading outcomes (per word, after read-aloud)

Each outcome has an ink color (text/border) and a soft color (background).
Each also has a **shape**, which is mandatory.

| Outcome | Ink | Soft | Shape (mandatory) |
|---|---|---|---|
| `correct` | `#268A3B` | `#DDF6E0` | Solid 3px underline |
| `substituted` | `#996300` | `#FFF1B8` | Wavy 2px underline |
| `omitted` | `#C62828` | `#FFE1E1` | Dashed 2px outline around word, word text at `ink-3` |
| `self_corrected` | `#0A7F8F` | `#D6F3F7` | Solid underline + small filled dot above word end |
| `inserted` | `#7041D0` | `#ECE4FB` | Caret marker `‸` between words; extra word shown on tap only |
| `pending` | `ink-4` | none | No underline. Default before reading |

All ink colors pass 4.5:1 on both `paper` and their own soft background.

### Mastery states (per unit)

| State | Fill | Border | Glyph color |
|---|---|---|---|
| `mastered` | `correct` ink `#268A3B` | same | `on-primary` |
| `practicing` | `substituted` soft `#FFF1B8`, bottom half filled with `#996300` at 25% | 2px `#996300` | `ink` |
| `unseen` | transparent | 2px dashed `line-strong` | `ink-3` |
| `excluded` (demo: deliberately removed) | `paper-sunken` | 2px `line` | `ink-4`, strikethrough |

Semantics are shared on purpose: green means "can read this" in both the
story and the grid. That lets the demo say "every word uses only green units".

### Data visualization (eval charts)

- Nepali series: `primary` `#1D6FE8`
- English series: `#996300` (amber ink)
- Target / threshold lines: `ink-3`, 1px dashed
- Gridlines: `line`. Axis text: `ink-3`, Plex Sans 12px
- Never more than 2 series colors on one chart. Label series directly, no legend box when avoidable.

---

## 3. Typography

All fonts from Google Fonts. Load only the weights listed.

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Andika:wght@400;700&family=Baloo+2:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans+Devanagari:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet">
```

| Role | Family | Why |
|---|---|---|
| `font-story-ne` | **Baloo 2** | Rounded, friendly, clean conjuncts at large sizes. Covers Devanagari + Latin |
| `font-story-en` | **Andika** | Designed for beginning readers: single-storey **a** and **g**, distinct I/l/1. Matches how children are taught to write |
| `font-ui` | **IBM Plex Sans**, **IBM Plex Sans Devanagari** | Same design family across both scripts, so the teacher grid looks consistent in Nepali and English |
| `font-mono` | **IBM Plex Mono** | Verifier log, unit signatures, eval numbers |

Never use Inter, Roboto, Poppins, Montserrat or system-ui as a display font.

### Child scale

| Token | Size / line-height | Weight | Use |
|---|---|---|---|
| `story-xl` | 48px / 1.8 | 500 (Baloo) / 400 (Andika) | Story text, tablet+ |
| `story-lg` | 40px / 1.8 | same | Story text, phone landscape |
| `story-md` | 32px / 1.75 | same | Story text, phone portrait. **Floor — never smaller** |
| `child-title` | 28px / 1.3 | 600 | Learner name, "Let's read!" |
| `child-label` | 20px / 1.4 | 600 | Button labels |

Story text rules:
- `word-spacing: 0.3em`. Children need visible word boundaries.
- Max 4 sentences visible at once; max line length 28 characters for Nepali, 32 for English.
- Left-aligned. Never justified, never centered for multi-line text.
- Each word is a `WordToken` (§6), not raw text.

### Adult scale

| Token | Size / line-height | Weight | Use |
|---|---|---|---|
| `display` | 32px / 1.2 | 600 | Page title (one per page) |
| `h2` | 20px / 1.3 | 600 | Section heading |
| `h3` | 16px / 1.4 | 600 | Card heading |
| `body` | 14px / 1.55 | 400 | Default text |
| `small` | 13px / 1.5 | 400 | Table cells, secondary |
| `caption` | 12px / 1.4 | 500 | Labels, axis, metadata. `ink-3` |
| `mono` | 13px / 1.6 | 400 | Logs, signatures |
| `stat` | 28px / 1.1 | 500, mono, `tabular-nums` | KPI numbers |

Use `font-variant-numeric: tabular-nums` on every number in a table, chart or stat.
Max weight is 600 (Baloo `700` allowed only for the child title). No letter-spacing tweaks.

---

## 4. Space, radius, elevation, motion

**Spacing:** 4px base. Allowed steps: 4, 8, 12, 16, 24, 32, 48, 64.
- Adult: 16px card padding, 24px between cards, 32px page gutter (16px on phone).
- Child: 24px minimum padding, 32px between story and controls.

**Radius:**

| Token | Value | Use |
|---|---|---|
| `radius-sm` | 4px | UnitChip in dense grids, badges, inputs |
| `radius-md` | 8px | **Default** for adult: cards, buttons, panels, popovers |
| `radius-lg` | 16px | Child surface only: story card, child buttons, illustration frame |
| `radius-xl` | 28px | Child surface only: learner tiles, big chunky buttons |
| `radius-full` | 9999px | Record button, avatar |

**Elevation.** Depth comes from borders and surface steps (`paper` → `card`), not shadows.
- Level 0: `paper`, no border
- Level 1: `card` + 1px `line` border. No shadow. (Most things.)
- Level 2: floating only (popover, dialog, toast): `card` + 1px `line` +
  `box-shadow: 0 1px 2px rgb(30 42 74 / .06), 0 8px 24px rgb(30 42 74 / .10)`

**Focus:** `outline: 2px solid var(--primary); outline-offset: 2px`. Always visible on keyboard focus.

**Motion.** Motion carries meaning only.
- Color/state change: 150ms `ease-out`
- WordToken outcome reveal: 200ms underline colour fade (from transparent)
- Mastery change in grid: one 400ms scale pulse (1 → 1.08 → 1), then settle
- Record button while listening: slow 1.6s ring pulse
- No page transitions, parallax, hover lifts, or entrance animations.
- `prefers-reduced-motion: reduce` → all durations 0, pulse becomes a static ring.

**Touch targets:** adult 40px minimum, child **64px** minimum.

---

## 5. Tailwind v4 tokens

Put this in `frontend/src/styles/theme.css`. Screens use these tokens only:
no raw hex, no arbitrary values like `p-[13px]`.

```css
@import "tailwindcss";

@theme {
  --color-paper: #EAF6FF;
  --color-paper-sunken: #D9EDFB;
  --color-card: #FFFFFF;
  --color-line: #CFE3F2;
  --color-line-strong: #8FB4D0;
  --color-ink: #1E2A4A;
  --color-ink-2: #3A4A6B;
  --color-ink-3: #55658A;
  --color-ink-4: #9AA8C2;

  --color-primary: #1D6FE8;
  --color-primary-hover: #1558BD;
  --color-primary-soft: #D9E8FF;
  --color-on-primary: #FFFFFF;
  --color-crimson: #C8102E;

  /* Child accents: decoration on the child surface (avatars, tiles, button edges). Meaning-free. */
  --color-sun: #FFC800;
  --color-sun-edge: #D19F00;
  --color-sun-soft: #FFF3BF;
  --color-coral: #FF5A5F;
  --color-coral-edge: #D13B40;
  --color-coral-soft: #FFE3E3;
  --color-leaf: #3DBB4F;
  --color-leaf-edge: #2A9239;
  --color-leaf-soft: #DDF6E0;
  --color-sky: #38A8FF;
  --color-sky-edge: #1C86D6;
  --color-sky-soft: #D6EEFF;
  --color-on-sun: #4A3600;

  --color-correct: #268A3B;
  --color-correct-soft: #DDF6E0;
  --color-substituted: #996300;
  --color-substituted-soft: #FFF1B8;
  --color-omitted: #C62828;
  --color-omitted-soft: #FFE1E1;
  --color-selfcorrected: #0A7F8F;
  --color-selfcorrected-soft: #D6F3F7;
  --color-inserted: #7041D0;
  --color-inserted-soft: #ECE4FB;

  --font-story-ne: "Baloo 2", "IBM Plex Sans Devanagari", sans-serif;
  --font-story-en: "Andika", "IBM Plex Sans", sans-serif;
  --font-ui: "IBM Plex Sans", "IBM Plex Sans Devanagari", sans-serif;
  --font-mono: "IBM Plex Mono", "IBM Plex Sans Devanagari", ui-monospace, monospace;

  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 20px;
  --radius-xl: 28px;

  --shadow-float: 0 1px 2px rgb(30 42 74 / .06), 0 8px 24px rgb(30 42 74 / .10);

  --ease-out: cubic-bezier(.2, .8, .2, 1);

  --container-story: 720px;  /* max-w-story; pair with box-content so padding sits outside */
}

@utility story-spacing { word-spacing: 0.3em; }

html { background: var(--color-paper); color: var(--color-ink); font-family: var(--font-ui); }
:focus-visible { outline: 2px solid var(--color-primary); outline-offset: 2px; }
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: 0s !important; transition-duration: 0s !important; }
}
```

---

## 6. Signature components

These five are what make Athena look designed. Build them first on a
`/styleguide` route with dummy data, then compose screens only from them plus
shadcn/ui primitives (Button, Dialog, Tabs, Tooltip, Table) restyled to these tokens.

### 6.1 `WordToken`

One word of story text.

```ts
{ text: string; lang: "ne" | "en"; outcome: "pending" | "correct" | "substituted"
  | "omitted" | "self_corrected"; active?: boolean; onTap?: () => void }
```

- Font: `font-story-ne` or `font-story-en` by `lang`; size inherits from story scale.
- `pending`: `ink` text, no decoration.
- `active` (word the child should read now, optional): `primary-soft` background, `radius-sm`, 2px horizontal padding. Only one active word at a time.
- Outcomes: exactly per §2 outcome table, including the shape. Underline offset 6px so it clears Devanagari descenders and lower matras (ु ू ृ).
- Tap → plays TTS for that word (when TTS exists). Tap target ≥ 64px tall via padding, not font size.
- Reveal animation: 200ms underline colour fade. `pending` keeps a transparent underline so the colour can transition.

### 6.2 `UnitChip`

One orthographic unit (akshara, matra, conjunct, or English grapheme).

```ts
{ unit: string; state: "mastered" | "practicing" | "unseen" | "excluded";
  size: "sm" | "lg"; changed?: "promoted" | "demoted" }
```

- `sm`: 36×36px, `radius-sm`, glyph 18px `font-ui`. For the adult grid.
- `lg`: 64×64px, `radius-lg`, glyph 32px `font-story-ne`. For the child screen.
- Matras are shown on the dotted circle placeholder: `◌ा`, `◌ि`, `◌ं`.
- State styling per §2 mastery table.
- `changed`: one pulse (§4), plus a 12px ↑ (correct ink) or ↓ (omitted ink) badge at top-right for the rest of the session.
- Tooltip (adult only): `seen 7 · streak 2 · updated 2m ago` in `caption` mono.

### 6.3 `MasteryGrid`

The learner's mastery set, **laid out the way Nepali children see it on the
classroom wall** (varnamala). Not a generic heatmap.

**Nepali** — rows, in this order, each labelled in `caption`:

```
स्वर (vowels)   अ आ इ ई उ ऊ ऋ ए ऐ ओ औ
क-वर्ग          क ख ग घ ङ
च-वर्ग          च छ ज झ ञ
ट-वर्ग          ट ठ ड ढ ण
त-वर्ग          त थ द ध न
प-वर्ग          प फ ब भ म
अन्तस्थ          य र ल व
ऊष्म            श ष स ह
संयुक्त          क्ष त्र ज्ञ  (+ any other conjuncts the learner has met)
मात्रा           ◌ा ◌ि ◌ी ◌ु ◌ू ◌ृ ◌े ◌ै ◌ो ◌ौ ◌ं ◌ँ ◌ः
```

Consonant rows sit on a 5-column grid so the vargas line up vertically, like the wall chart.

**English** — rows follow the synthetic-phonics sequence:

```
Set 1   s a t p i n
Set 2   m d g o c k
Set 3   ck e u r h b f l
Set 4   ff ll ss j v w x y z qu
Digraphs   sh ch th ng
Vowel teams   ai ee igh oa oo ar or ur ow oi ear
Tricky words   the said one was ... (UnitChip with a small ♥ marker)
```

- Header strip: learner avatar + name, a summary in mono (`31 / 33 consonants`, `9 / 13 matras`, `2 / 3 conjuncts`), and a legend showing all four states with their shapes.
- `sm` chips in adult views, `lg` chips (vowels + consonants only) on the child screen.
- Must print legibly in grayscale.

### 6.4 `VerifierLog`

The demo's money shot: "model proposes, code decides". It should look like an
instrument readout, not a chat transcript.

```ts
{ attempts: { n: number; text: string; violations: { word: string; unit: string; index: number }[];
  ms: number; model: string }[]; outcome: "verified" | "template_fallback" }
```

- Container: `paper-sunken`, 1px `line`, `radius-md`, `font-mono` 13px.
- One block per attempt, joined by a vertical 1px `line` timeline with a 10px node per attempt:
  - Node: hollow `omitted` ring if violations > 0, filled `correct` dot if 0.
  - Header line: `attempt 1 · gemini-3-flash · 1,240 ms · 3 violations` (`ink-3`, the count in `omitted` ink).
  - Story text in mono with violating words shown as `omitted` ink + strikethrough + `omitted-soft` background, and the offending unit in a superscript chip, e.g. `क्ष ✗`.
- Final line: `✓ 0 violations shipped` in `correct` ink, 600 weight, or `↺ template fallback` in `substituted` ink.
- Attempts reveal one by one (150ms stagger) only on first render.

### 6.5 `StoryCard`

The child's page.

- `card` surface, `radius-lg`, 1px `line`, max-width 720px, centered.
- Illustration on top: 4:3, `radius-lg` top corners, `paper-sunken` placeholder while loading with a quiet 3-dot loader (no spinner, no skeleton shimmer).
- Story text below in `WordToken`s, 32px padding.
- Bottom bar: one **record button** (96px circle, `primary`, mic icon, `radius-full`) centered, with "Next" (`child-label`) on the right only after reading. Nothing else.
- Language badge top-left (`ने` / `EN`, `caption`, `paper-sunken` pill).

### 6.6 `RiverCrossing`

Progress for the card check (placement game): the child's favourite animal crosses a river.

- Inline SVG, full width, 16:5. Near bank left, far bank right: `leaf-soft` with `leaf` grass tufts.
  Water between: `sky-soft` with 2–3 `sky` wave lines.
- One stepping stone per round, evenly spaced. **Shape + colour** per state: passed = `leaf` stone
  with a white ✓; current = `sun` stone, slightly larger; ahead = `card` stone with `line-strong` edge.
- The animal (its cached word picture, round, white ring) stands on the current stone and hops to
  the next with a 400 ms ease-out arc. On the far bank at the end, with a `sun` flag.
- Reduced motion: no hop, it just appears on the new stone.
- Accessible: `role="img"` with "Round 3 of 6" label.

---

## 7. Screens (composition only)

| Screen | Surface | Composed from |
|---|---|---|
| Learner pick | Child | Avatar tiles (`lg` radius, 120px), name in `child-title` |
| Story / read | Child | `StoryCard`, `WordToken` |
| Result | Child | `StoryCard` with outcomes + a compact strip of `lg` `UnitChip`s that changed |
| Mastery | Adult | `MasteryGrid` (ne/en tabs) |
| Generation detail | Adult | `VerifierLog` + illustration thumb + cost/latency stats |
| Teacher | Adult | Learner × unit heatmap table built from `sm` `UnitChip`s, sticky first column |
| Eval | Adult | Stat row + two-series bar chart (§2 dataviz) |
| Printable pack | Print | `@media print`: no chrome, `paper` → white, story text 28pt, outcomes off, a practice sheet of `lg` chips for the weakest units |

Adult layout: 240px left nav (`paper-sunken`, `body` links, active item `primary-soft`), content max-width 1200px.
Child layout: no nav. A single back arrow (64px, top-left) only.

---

## 8. Iconography and illustration

**Icons:** `lucide-react`, 1.75px stroke, 20px adult / 32px child, color `currentColor`.
No emoji in UI. The only non-lucide glyphs allowed are ✓ ✗ ↑ ↓ ↺ ‸ ♥ in mono contexts.

**Illustrations:** generated, and must look like they belong to the UI. Append this to every illustrator prompt:

> Simple flat vector children's book illustration. Light sky background
> #EAF6FF. Bright palette: sky blue #38A8FF, leaf green #3DBB4F, sunny yellow
> #FFC800, coral red #FF5A5F, deep navy #1E2A4A for outlines. Soft rounded shapes, no gradients, no text, no letters. Animals or
> objects as main characters; any people shown small, simple, no detailed faces.
> Not photorealistic. Setting: rural or small-town Nepal.

---

## 9. Do / Don't

**Do**
- Use tokens only. No hex values in components.
- Use one `primary` button per view at most.
- Use real Nepali words with conjuncts and lower matras in every mock and styleguide entry.
- Use tabular numbers everywhere numbers align.
- Check the child screen at 360px wide.

**Don't**
- Gradients, glassmorphism, blurred blobs, gradient text, neon glows.
- Purple/indigo SaaS accents, dark mode, pure black backgrounds.
- Inter, Poppins, Montserrat, Roboto.
- Emoji as icons, confetti, celebratory animations that cost a child's attention.
- Shadows on resting cards. Hover lift effects.
- `rounded-2xl`+ outside the child surface. Mixed radii within one view.
- Color as the only signal for any state.
- Centered multi-line body text.
- Lorem ipsum or English placeholder text in Nepali slots.

---

## 10. Prompts for the agent

- "Build `WordToken` per DESIGN.md §6.1 and add all outcome states to `/styleguide` with the Nepali word क्षेत्र and the English word ship."
- "Build `MasteryGrid` per §6.3 for Nepali with 2 consonants excluded and 3 practicing; show it in grayscale print preview."
- "Build `VerifierLog` per §6.4 from this attempts JSON: …"
- "Compose the Story/read screen from §7 using only existing components."
