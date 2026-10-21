import { BookOpen } from 'lucide-react'
import type { components } from '../api-types'
import { bi } from '../ui'
import { neNum } from './LevelStars'
import { UnitChip } from './UnitChip'

export type Stage = components['schemas']['StageOut']

// DESIGN.md §6.7: reading level 1-10 (athena/stages.py) with progress to the next level.

/** The level number in a round `leaf` badge. */
export function LevelNumber({ n, size = 'sm' }: { n: number; size?: 'sm' | 'lg' }) {
  const cls = size === 'lg' ? 'size-10 text-child-label' : 'size-5 text-caption'
  return (
    <span aria-hidden className={`inline-flex shrink-0 items-center justify-center rounded-full bg-leaf font-bold tabular-nums text-on-primary ${cls}`}>
      {n}
    </span>
  )
}

/** "3 more letters to Level 5" / "4 more letters to learn them all" / "All letters learned" */
function nextLabel(stage: Stage, lang: 'ne' | 'en'): string {
  const left = stage.next_at - stage.mastered
  const unit = (lang === 'ne' ? 'letter' : 'sound') + (left === 1 ? '' : 's')
  const ne = lang === 'ne' ? 'अक्षर' : 'ध्वनि'
  if (left <= 0) return bi(`सबै ${ne} सिकियो`, `All ${lang === 'ne' ? 'letters' : 'sounds'} learned`)
  if (!stage.next_name) return bi(`सबै सिक्न ${neNum(left)} ${ne} बाँकी`, `${left} more ${unit} to learn them all`)
  return bi(`तह ${neNum(stage.n + 1)} सम्म ${neNum(left)} ${ne} बाँकी`, `${left} more ${unit} to ${stage.next_name}`)
}

export function StageBadge({
  stage,
  lang,
  variant = 'compact',
  className = '',
}: {
  stage: Stage
  lang: 'ne' | 'en'
  variant?: 'full' | 'compact'
  className?: string
}) {
  const label = `Reading level ${stage.n} of 10, ${stage.mastered} of ${stage.total} ${lang === 'ne' ? 'letters' : 'sounds'}`
  if (variant === 'compact') {
    return (
      <span
        role="img"
        aria-label={label}
        className={`inline-flex items-center gap-1 rounded-full border border-line bg-card px-2 py-0.5 font-semibold text-ink ${className}`}
      >
        {stage.name}
      </span>
    )
  }
  const span = Math.max(1, stage.next_at - stage.start)
  const pct = Math.min(100, ((stage.mastered - stage.start) / span) * 100)
  return (
    <span role="img" aria-label={label} className={`flex w-full flex-col gap-1.5 ${className}`}>
      <span className="flex items-center justify-center gap-2 text-child-label font-bold text-ink">
        {bi('तह', 'Level')}
        <LevelNumber n={stage.n} size="lg" />
      </span>
      <span className="block h-3 w-full overflow-hidden rounded-full bg-line">
        <span className="block h-full rounded-full bg-leaf" style={{ width: `${pct}%` }} />
      </span>
      <span className="text-small font-semibold text-ink-2">{nextLabel(stage, lang)}</span>
    </span>
  )
}

/** DESIGN.md §6.8: shown on the result screen when a reading moved the child forward. */
export function LevelUpCard({
  before,
  after,
  sizeUp,
  learned,
  lang,
}: {
  before: Stage
  after: Stage
  sizeUp: boolean
  learned: string[]
  lang: 'ne' | 'en'
}) {
  const levelUp = after.n > before.n
  if (!levelUp && !sizeUp && learned.length === 0) return null
  return (
    <div className="mb-4 flex flex-col gap-3 rounded-lg border border-sun-edge bg-sun-soft px-4 py-3">
      {levelUp && (
        <p className="m-0 flex items-center gap-3 text-child-label font-bold text-ink">
          <LevelNumber n={after.n} size="lg" /> {bi(`तह ${neNum(after.n)} पुग्यौ!`, `You reached ${after.name}!`)}
        </p>
      )}
      {sizeUp && (
        <p className="m-0 flex items-center gap-3 text-child-label font-bold text-ink">
          <BookOpen size={32} strokeWidth={1.75} className="shrink-0 text-primary" aria-hidden />
          {bi('अब अलि ठूला कथा!', 'Bigger stories now!')}
        </p>
      )}
      {learned.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-child-label font-bold text-ink">{bi('नयाँ सिकेका', 'New letters learned')}</span>
          {learned.map((u) => (
            <UnitChip key={u} unit={u} state="mastered" size="lg" lang={lang} changed="promoted" />
          ))}
        </div>
      )}
    </div>
  )
}
