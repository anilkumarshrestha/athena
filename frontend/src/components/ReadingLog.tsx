import type { ReadResult } from '../api'

// Adult readout of one read-aloud: what STT heard and what was scored. Same
// instrument style as VerifierLog (DESIGN.md §6.4).

const glyph = (sig: string) => sig.slice(sig.indexOf(':') + 1)

const MARK: Record<string, string> = {
  correct: 'text-correct',
  self_corrected: 'text-selfcorrected',
  substituted: 'text-substituted',
  omitted: 'text-omitted line-through',
}

export function ReadingLog({ result }: { result: ReadResult }) {
  const errors = Object.entries(result.unit_errors)
  return (
    <section className="rounded-md border border-line bg-paper-sunken p-4 font-mono text-mono">
      <div className="text-ink-3 tabular-nums">
        reading · {result.engine} · {result.stt_ms.toLocaleString()} ms · {result.words_correct}/{result.words.length}{' '}
        words · {result.wcpm} wcpm
      </div>
      <div className="mt-1 text-ink">heard: {result.transcript || '(nothing)'}</div>
      <div className="mt-1">
        {result.words.map((w) => (
          <span key={w.index} className={MARK[w.outcome] ?? 'text-ink'}>
            {w.expected}
            {w.outcome === 'substituted' && w.heard ? `→${w.heard}` : ''}{' '}
          </span>
        ))}
      </div>
      {result.insertions.length > 0 && (
        <div className="mt-1 text-inserted">‸ extra: {result.insertions.map((i) => i.word).join(' ')}</div>
      )}
      <div className={`mt-1 ${errors.length ? 'text-omitted' : 'text-correct'}`}>
        {errors.length
          ? `units to practise: ${errors.map(([u, n]) => `${glyph(u)}×${n}`).join(' ')}`
          : '✓ no unit errors'}
      </div>
    </section>
  )
}
