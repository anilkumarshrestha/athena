import type { Language } from '../api'

export type Outcome = 'pending' | 'correct' | 'substituted' | 'omitted' | 'self_corrected'

// DESIGN.md §2 outcome table: colour AND shape for every state.
const OUTCOME: Record<Outcome, string> = {
  pending: 'text-ink',
  correct: 'text-ink underline decoration-correct decoration-solid decoration-[3px]',
  substituted: 'text-ink underline decoration-substituted decoration-wavy decoration-2',
  omitted: 'text-ink-3 outline-2 outline-dashed outline-omitted rounded-sm',
  self_corrected: 'text-ink underline decoration-selfcorrected decoration-solid decoration-[3px] relative',
}

export function WordToken({
  text,
  lang,
  outcome = 'pending',
  active = false,
  onTap,
}: {
  text: string
  lang: Language
  outcome?: Outcome
  active?: boolean
  onTap?: () => void
}) {
  return (
    <span
      onClick={onTap}
      className={[
        'inline-block px-0.5 underline-offset-[6px] transition-colors duration-150',
        lang === 'ne' ? 'font-story-ne font-medium' : 'font-story-en',
        OUTCOME[outcome],
        active ? 'bg-primary-soft rounded-sm' : '',
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
