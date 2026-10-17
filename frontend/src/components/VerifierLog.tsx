import type { Attempt, Story } from '../api'

// DESIGN.md §6.4: "model proposes, code decides". An instrument readout.

const norm = (w: string) => w.toLowerCase().replace(/[.,!?;:"'“”‘’()।॥\-—–…]/g, '')

function AttemptText({ attempt }: { attempt: Attempt }) {
  const bad = new Map<string, string | null>()
  for (const v of attempt.violations) if (!bad.has(v.word)) bad.set(v.word, v.unit ?? null)
  const lines = [attempt.title, ...attempt.sentences]
  return (
    <div className="mt-1 text-ink">
      {lines.map((line, i) => (
        <div key={i}>
          {line.split(/\s+/).filter(Boolean).map((w, j) => {
            const key = norm(w)
            if (!bad.has(key)) return <span key={j}>{w} </span>
            const unit = bad.get(key)
            return (
              <span key={j}>
                <span className="bg-omitted-soft text-omitted line-through">{w}</span>
                <sup className="ml-0.5 rounded-sm bg-omitted-soft px-1 text-omitted no-underline">
                  {unit ? unit.split(':')[1] : '?'} ✗
                </sup>{' '}
              </span>
            )
          })}
        </div>
      ))}
    </div>
  )
}

export function VerifierLog({ story }: { story: Story }) {
  const fallback = story.outcome === 'pruned' || story.outcome === 'wordlist'
  return (
    <section className="rounded-md border border-line bg-paper-sunken p-4 font-mono text-mono">
      <ol className="relative m-0 list-none border-l border-line p-0 pl-5">
        {story.attempts.map((a) => (
          <li key={a.n} className="relative mb-4">
            <span
              className={`absolute -left-[26px] top-1.5 size-2.5 rounded-full ${
                a.violations.length ? 'border-2 border-omitted bg-paper-sunken' : 'bg-correct'
              }`}
            />
            <div className="text-ink-3 tabular-nums">
              attempt {a.n} · {a.model} · {a.ms.toLocaleString()} ms ·{' '}
              <span className={a.violations.length ? 'text-omitted' : 'text-correct'}>
                {a.violations.length} violations
              </span>
            </div>
            <AttemptText attempt={a} />
          </li>
        ))}
      </ol>
      <div className={`font-semibold ${fallback ? 'text-substituted' : 'text-correct'}`}>
        {fallback ? `↺ fallback (${story.outcome}) · 0 violations shipped` : '✓ 0 violations shipped'}
      </div>
      <div className="mt-1 text-ink-3 tabular-nums">
        units used: {story.units_used.map((u) => u.split(':')[1]).join(' ')}
      </div>
    </section>
  )
}
