import type { Language } from '../api'

export type Outcome = 'pending' | 'correct' | 'substituted' | 'omitted' | 'self_corrected'

// DESIGN.md §2 outcome table: colour AND shape for every state.
// Pending keeps a transparent underline so the outcome colour fades in (§4).
const OUTCOME: Record<Outcome, string> = {
  pending: 'text-ink decoration-transparent decoration-3',
  correct: 'text-ink decoration-correct decoration-solid decoration-3',
  substituted: 'text-ink decoration-substituted decoration-wavy decoration-2',
  omitted: 'text-ink-3 outline-2 outline-dashed outline-omitted rounded-sm',
  self_corrected: 'text-ink decoration-selfcorrected decoration-solid decoration-3 relative',
}

export function WordToken({
  text,
  lang,
  outcome = 'pending',
  active = false,
  selected = false,
  dataWord,
  onTap,
}: {
  text: string
  lang: Language
  outcome?: Outcome
  active?: boolean
  selected?: boolean // tapped for help: filled + ringed (shape, not colour alone)
  dataWord?: number
  onTap?: () => void
}) {
  return (
    <span
      data-word={dataWord}
      aria-pressed={onTap ? selected : undefined}
      onClick={onTap}
      role={onTap ? 'button' : undefined}
      tabIndex={onTap ? 0 : undefined}
      onKeyDown={onTap ? (e) => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), onTap()) : undefined}
      className={[
        'inline-block px-0.5 underline-offset-6 transition-colors duration-200',
        outcome === 'omitted' ? '' : 'underline',
        lang === 'ne' ? 'font-story-ne font-medium' : 'font-story-en',
        OUTCOME[outcome],
        active ? 'bg-primary-soft rounded-sm' : '',
        selected ? 'rounded-sm bg-primary-soft ring-2 ring-primary' : '',
        onTap ? 'cursor-pointer' : '',
      ].join(' ')}
    >
      {text}
      {outcome === 'self_corrected' && (
        <span aria-hidden className="absolute -top-1 right-0 size-2 rounded-full bg-selfcorrected" />
      )}
    </span>
  )
}
