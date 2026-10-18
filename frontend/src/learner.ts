import type { Learner } from './api'

// Small helpers about one child, shared by "Who's reading?", the child's home and grown-ups.

// Decorative child accents, cycled by index. Full class strings so Tailwind sees them.
export const ACCENTS = [
  { tile: 'bg-sky-soft border-sky', ring: 'border-sky', btn: 'bg-sky border-sky-edge text-on-primary' },
  { tile: 'bg-sun-soft border-sun', ring: 'border-sun', btn: 'bg-sun border-sun-edge text-on-sun' },
  { tile: 'bg-leaf-soft border-leaf', ring: 'border-leaf', btn: 'bg-leaf border-leaf-edge text-on-primary' },
  { tile: 'bg-coral-soft border-coral', ring: 'border-coral', btn: 'bg-coral border-coral-edge text-on-primary' },
] as const

/** A child's accent stays the same everywhere (from the id, not the list position). */
export function accentOf(id: string) {
  let h = 0
  for (const c of id) h = (h * 31 + c.charCodeAt(0)) >>> 0
  return ACCENTS[h % ACCENTS.length]
}

const BUDDY_NE: Record<string, string> = { cat: 'बिरालो', dog: 'कुकुर', goat: 'बाख्रा', bird: 'चरा', rabbit: 'खरायो' }
export const buddyNe = (l: Learner) => BUDDY_NE[l.profile.buddy ?? 'cat'] ?? 'बिरालो'
export const buddyEn = (l: Learner) => l.profile.buddy ?? 'cat'
export const goalOf = (l: Learner) => Number(l.profile.daily_goal ?? 10)
export const learns = (l: Learner, lang: 'ne' | 'en') => (l.profile.languages ?? 'both') === 'both' || l.profile.languages === lang

// Stars last seen on this device, per child: a gained star is celebrated once.
const STARS_KEY = 'athena.stars'
const starTotal = (l: Learner) => (l.level.ne ?? 1) + (l.level.en ?? 1) + (l.maths_level.ne ?? 1) + (l.maths_level.en ?? 1)

/** True once when this child has more stars than last time on this device. */
export function gainedStar(l: Learner): boolean {
  try {
    const seen = JSON.parse(localStorage.getItem(STARS_KEY) ?? '{}') as Record<string, number>
    const before = seen[l.id]
    seen[l.id] = starTotal(l)
    localStorage.setItem(STARS_KEY, JSON.stringify(seen))
    return before !== undefined && seen[l.id] > before
  } catch {
    return false // storage blocked: no celebration, nothing else changes
  }
}
