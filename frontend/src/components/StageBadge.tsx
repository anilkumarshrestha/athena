import { BookOpen, Flower2, Leaf, Sprout, TreeDeciduous, Trees, type LucideIcon } from 'lucide-react'
import type { components } from '../api-types'
import { bi } from '../ui'
import { neNum } from './LevelStars'
import { UnitChip } from './UnitChip'

export type Stage = components['schemas']['StageOut']

// DESIGN.md §6.7: reading stage (athena/stages.py). Names stay English in every language.
const ICON: Record<number, LucideIcon> = { 1: Sprout, 2: Leaf, 3: Flower2, 4: TreeDeciduous, 5: Trees }

export function StageIcon({ n, size = 20 }: { n: number; size?: number }) {
  const Icon = ICON[n] ?? Sprout
  return <Icon size={size} strokeWidth={1.75} className="shrink-0 text-leaf-edge" aria-hidden />
}

/** "3 more letters to Flower" / "All letters learned" */
function nextLabel(stage: Stage, lang: 'ne' | 'en'): string {
  const unit = lang === 'ne' ? 'letters' : 'sounds'
  if (stage.next_at == null || !stage.next_name) return bi(lang === 'ne' ? 'सबै अक्षर सिकियो' : 'सबै ध्वनि सिकियो', `All ${unit} learned`)
  const left = stage.next_at - stage.mastered
  return bi(`${stage.next_name} सम्म ${neNum(left)} ${lang === 'ne' ? 'अक्षर' : 'ध्वनि'} बाँकी`, `${left} more ${unit} to ${stage.next_name}`)
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
  const label = `Reading stage ${stage.name}, ${stage.mastered} of ${stage.total} ${lang === 'ne' ? 'letters' : 'sounds'}`
  if (variant === 'compact') {
    return (
      <span
        role="img"
        aria-label={label}
        className={`inline-flex items-center gap-1 rounded-full border border-line bg-card px-2 py-0.5 font-semibold text-ink ${className}`}
      >
        <StageIcon n={stage.n} size={14} />
        {stage.name}
      </span>
    )
  }
  const span = stage.next_at == null ? 1 : Math.max(1, stage.next_at - stage.start)
  const pct = stage.next_at == null ? 100 : Math.min(100, ((stage.mastered - stage.start) / span) * 100)
  return (
    <span role="img" aria-label={label} className={`flex w-full flex-col gap-1.5 ${className}`}>
      <span className="flex items-center justify-center gap-2 text-child-label font-bold text-ink">
        <StageIcon n={stage.n} size={32} />
        {stage.name}
      </span>
      <span className="block h-3 w-full overflow-hidden rounded-full bg-line">
        <span className="block h-full rounded-full bg-leaf" style={{ width: `${pct}%` }} />
      </span>
      <span className="text-small font-semibold text-ink-2">{nextLabel(stage, lang)}</span>
    </span>
  )
}

/** DESIGN.md §6.8: shown once on the result screen when a reading moved the child forward. */
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
  const stageUp = after.n > before.n
  if (!stageUp && !sizeUp && learned.length === 0) return null
  return (
    <div className="mb-4 flex flex-col gap-3 rounded-lg border border-sun-edge bg-sun-soft px-4 py-3">
      {stageUp && (
        <p className="m-0 flex items-center gap-3 text-child-label font-bold text-ink">
          <StageIcon n={after.n} size={32} /> {bi(`${after.name} पुग्यौ!`, `You reached ${after.name}!`)}
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
