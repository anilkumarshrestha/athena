import type { Attempt, Language, Story } from '../api'
import { unitGlyph } from '../units'

// DESIGN.md §6.4: "model proposes, code decides". An instrument readout.

// Mirror the verifiers' tokenizers (athena/verifier/{nepali,english}.py) so a
// violation's word matches what is on screen: NFC, no ZWJ/ZWNJ, same splits.
const NE_SPLIT = /[\s।॥,.?!;:"'“”‘’()[\]\-—–…]+/
const EN_WORD = /[a-z]+(?:'[a-z]+)?/g
function tokens(w: string, lang: Language): string[] {
  const s = w.normalize('NFC').replace(/[\u200c\u200d]/g, '')
  return lang === 'ne' ? s.split(NE_SPLIT).filter(Boolean) : (s.toLowerCase().replace(/’/g, "'").match(EN_WORD) ?? [])
}

function AttemptText({ attempt, lang }: { attempt: Attempt; lang: Language }) {
  const bad = new Map<string, Set<string>>()
  for (const v of attempt.violations) {
    const units = bad.get(v.word) ?? new Set<string>()
    units.add(v.unit ? unitGlyph(v.unit) : '?')
    bad.set(v.word, units)
  }
  const lines = [attempt.title, ...attempt.sentences]
  return (
    <div className="mt-1 text-ink">
      {lines.map((line, i) => (
        <div key={i}>
          {line.split(/\s+/).filter(Boolean).map((w, j) => {
            const units = new Set(tokens(w, lang).flatMap((t) => [...(bad.get(t) ?? [])]))
            if (!units.size) return <span key={j}>{w} </span>
            return (
              <span key={j}>
                <span className="bg-omitted-soft text-omitted line-through">{w}</span>
                <sup className="ml-0.5 rounded-sm bg-omitted-soft px-1 text-omitted no-underline">
                  {[...units].join(' ')} ✗
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
  const fallback = ['pruned', 'template', 'wordlist'].includes(story.outcome)
  return (
    <section className="rounded-md border border-line bg-paper-sunken p-4 font-mono text-mono">
      <ol className="relative m-0 list-none border-l border-line p-0 pl-5">
        {story.attempts.map((a) => (
          <li key={a.n} className="relative mb-4">
            <span
              className={`absolute -left-6.5 top-1.5 size-2.5 rounded-full ${
                a.violations.length ? 'border-2 border-omitted bg-paper-sunken' : 'bg-correct'
              }`}
            />
            <div className="text-ink-3 tabular-nums">
              attempt {a.n} · {a.model} · {a.ms.toLocaleString()} ms ·{' '}
              <span className={a.violations.length ? 'text-omitted' : 'text-correct'}>
                {a.violations.length} {a.violations.length === 1 ? 'violation' : 'violations'}
              </span>
            </div>
            <AttemptText attempt={a} lang={story.language} />
          </li>
        ))}
      </ol>
      <div className={`font-semibold ${fallback ? 'text-substituted' : 'text-correct'}`}>
        {fallback ? `↺ fallback (${story.outcome}) · 0 violations shipped` : '✓ 0 violations shipped'}
      </div>
      <div className="mt-1 text-ink-3 tabular-nums">
        units used: {story.units_used.map(unitGlyph).join(' ')}
      </div>
    </section>
  )
}
