import { Star } from 'lucide-react'
import type { Learner } from '../api'

// Level as stars (1-3): growth, not a grade. Filled vs outlined stars (shape, not colour
// alone, DESIGN.md §2); the number is in the label for screen readers and grown-ups.
export function LevelStars({ level, size = 16, className = '' }: { level: number; size?: number; className?: string }) {
  return (
    <span className={`inline-flex items-center gap-0.5 ${className}`} role="img" aria-label={`level ${level} of 3`}>
      {[1, 2, 3].map((i) => (
        <Star key={i} size={size} strokeWidth={2} className={i <= level ? 'fill-sun text-sun-edge' : 'text-ink-4'} />
      ))}
    </span>
  )
}

const NE = '०१२३४५६७८९'
export const neNum = (n: number) => String(n).replace(/\d/g, (d) => NE[+d])

/** Letters (Nepali) or sounds (English) the child reads confidently: mastered units. */
export function knownCount(l: Learner, lang: 'ne' | 'en'): number {
  return (l.units[lang] ?? []).filter((u) => u.state === 'mastered').length
}
