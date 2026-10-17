import type { Language } from './api'

// Mastery signatures (athena/verifier/*.py):
//   c:<x> consonant / independent vowel   m:<x> matra, modifier, halanta
//   k:<x> conjunct (mastered whole)        g:<x> English grapheme   w:<x> tricky word

export type UnitState = 'mastered' | 'practicing' | 'unseen' | 'excluded'

export type UnitRow = { label: string; units: string[]; childVisible?: boolean }

const row = (label: string, prefix: string, units: string, childVisible = false): UnitRow => ({
  label,
  units: units.split(' ').map((u) => prefix + u),
  childVisible,
})

// DESIGN.md §6.3: the varnamala wall chart, in classroom order.
const NE_ROWS: UnitRow[] = [
  row('स्वर', 'c:', 'अ आ इ ई उ ऊ ऋ ए ऐ ओ औ', true),
  row('क-वर्ग', 'c:', 'क ख ग घ ङ', true),
  row('च-वर्ग', 'c:', 'च छ ज झ ञ', true),
  row('ट-वर्ग', 'c:', 'ट ठ ड ढ ण', true),
  row('त-वर्ग', 'c:', 'त थ द ध न', true),
  row('प-वर्ग', 'c:', 'प फ ब भ म', true),
  row('अन्तस्थ', 'c:', 'य र ल व', true),
  row('ऊष्म', 'c:', 'श ष स ह', true),
  row('संयुक्त', 'k:', 'क्ष त्र ज्ञ'),
  row('मात्रा', 'm:', 'ा ि ी ु ू ृ े ै ो ौ ं ँ ः ्'),
]

// Synthetic-phonics sequence, limited to graphemes in data/en_lexicon.json.
const EN_ROWS: UnitRow[] = [
  row('Set 1', 'g:', 's a t p i n', true),
  row('Set 2', 'g:', 'm d g o c k', true),
  row('Set 3', 'g:', 'ck e u r h b f l', true),
  row('Set 4', 'g:', 'ff ll ss j v w x y z zz qu', true),
  row('Digraphs', 'g:', 'sh ch th ng wh ph tch'),
  row('Vowel teams', 'g:', 'ai ee igh oa oo ar or ur ow oi ear air ure er'),
  row('Alternatives', 'g:', 'ay ea ou ie aw ir ew oy ue ey oe au'),
  row('Split vowels', 'g:', 'a_e i_e o_e u_e e_e'),
  row('More spellings', 'g:', 'ed kn wr mb dge'),
  row('Tricky words', 'w:', 'i a the to no go so he she we me be was you they my said have like do'),
]

/** Chart rows for a language, plus an "other" row so no mastered unit is ever hidden. */
export function chartRows(lang: Language, known: Iterable<string>): UnitRow[] {
  const rows = lang === 'ne' ? NE_ROWS : EN_ROWS
  const placed = new Set(rows.flatMap((r) => r.units))
  const extra = [...known].filter((u) => !placed.has(u))
  const conj = extra.filter((u) => u.startsWith('k:'))
  const rest = extra.filter((u) => !u.startsWith('k:'))
  return rows
    .map((r) => (r.units[0].startsWith('k:') ? { ...r, units: [...r.units, ...conj] } : r))
    .concat(rest.length ? [{ label: lang === 'ne' ? 'अरू' : 'Other', units: rest }] : [])
}

/** What the child sees on a chip. Matras sit on a dotted circle; split vowels read a–e. */
export function unitGlyph(sig: string): string {
  const kind = sig.slice(0, 2)
  const g = sig.slice(2)
  if (kind === 'm:') return '◌' + g
  if (kind === 'g:' && g.includes('_')) return g.replace('_', '–')
  return g
}

export const KIND_LABEL: Record<string, string> = {
  'c:': 'letters',
  'm:': 'matras',
  'k:': 'conjuncts',
  'g:': 'sounds',
  'w:': 'tricky words',
}
