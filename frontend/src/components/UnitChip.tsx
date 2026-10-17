import { unitGlyph, type UnitState } from '../units'

// DESIGN.md §2 mastery table + §6.2. Every state differs by shape, not only colour:
// filled / half-filled / dashed outline / struck through. Survives grayscale print.
const STATE: Record<UnitState, string> = {
  mastered: 'border-2 border-correct bg-correct text-on-primary',
  practicing: 'border-2 border-substituted bg-substituted-soft text-ink',
  unseen: 'border-2 border-dashed border-line-strong text-ink-3',
  excluded: 'border-2 border-line bg-paper-sunken text-ink-4 line-through',
}

const SIZE = {
  sm: 'h-9 min-w-9 px-1.5 rounded-sm text-unit-sm',
  lg: 'h-16 min-w-16 px-3 rounded-lg text-story-md leading-none',
}

export function UnitChip({
  unit,
  state,
  size = 'sm',
  lang = 'ne',
  changed,
  detail,
}: {
  unit: string
  state: UnitState
  size?: 'sm' | 'lg'
  lang?: 'ne' | 'en'
  changed?: 'promoted' | 'demoted'
  detail?: string
}) {
  const glyph = unitGlyph(unit)
  const font = size === 'sm' ? 'font-ui' : lang === 'ne' ? 'font-story-ne' : 'font-story-en'
  return (
    <span
      role="img"
      aria-label={`${glyph}: ${state}${changed ? `, ${changed}` : ''}`}
      title={detail ?? `${glyph} · ${state}`}
      className={[
        'relative inline-flex shrink-0 items-center justify-center overflow-visible leading-none tabular-nums',
        font,
        SIZE[size],
        STATE[state],
        changed ? 'animate-chip-pulse' : '',
      ].join(' ')}
    >
      {state === 'practicing' && (
        <span aria-hidden className="absolute inset-x-0 bottom-0 h-1/2 bg-substituted/25" />
      )}
      <span className="relative">
        {unit.startsWith('w:') && <span aria-hidden className="mr-1 text-caption">♥</span>}
        {glyph}
      </span>
      {changed && (
        <span
          aria-hidden
          className={`absolute -right-1.5 -top-1.5 flex size-4 items-center justify-center rounded-full bg-card text-caption font-semibold ${
            changed === 'promoted' ? 'text-correct' : 'text-omitted'
          }`}
        >
          {changed === 'promoted' ? '↑' : '↓'}
        </span>
      )}
    </span>
  )
}
