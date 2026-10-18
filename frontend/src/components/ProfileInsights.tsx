import { useEffect, useState } from 'react'
import type { components } from '../api-types'
import { api, type Language } from '../api'
import { unitGlyph } from '../units'
import { DotLoader } from './DotLoader'

type Insights = components['schemas']['InsightsOut']

// Learner profile for parents: a short note (model phrases facts computed in code),
// strengths and gaps by skill group, mistake patterns, pace. Status is text + bar, not colour alone.

const STATUS = {
  strong: { ne: 'बलियो', en: 'strong', bar: 'bg-correct' },
  learning: { ne: 'सिक्दै', en: 'learning', bar: 'bg-substituted' },
  not_started: { ne: 'सुरु भएको छैन', en: 'not started', bar: 'bg-line-strong' },
} as const

const TREND = { up: '↑ improving', down: '↓ slower lately', flat: '→ steady', unknown: '— not enough readings yet' } as const

export function ProfileInsights({ learnerId, lang }: { learnerId: string; lang: Language }) {
  const [ins, setIns] = useState<Insights | null>(null)
  const [note, setNote] = useState<{ ne: string; en: string } | null>(null)

  useEffect(() => {
    setIns(null)
    setNote(null)
    api.insights(learnerId, lang).then(setIns).catch(() => {})
    api.summary(learnerId, lang).then(setNote).catch(() => {})
  }, [learnerId, lang])

  if (!ins) return <div className="mb-8"><DotLoader /></div>
  const p = ins.pace

  return (
    <section className="mb-8">
      <h2 className="mb-3 text-h2 font-semibold">प्रोफाइल · Profile</h2>

      <div className="mb-4 rounded-xl border-2 border-line bg-card p-4">
        {note === null ? (
          <div className="flex items-center gap-3 text-small text-ink-3"><DotLoader /> writing a short note…</div>
        ) : note.ne || note.en ? (
          <>
            <p className="m-0 mb-2 font-story-ne text-body">{note.ne}</p>
            <p className="m-0 text-small text-ink-2">{note.en}</p>
          </>
        ) : (
          <p className="m-0 text-small text-ink-3">Note unavailable; the details below are complete.</p>
        )}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-xl border-2 border-line bg-card p-4">
          <h3 className="m-0 mb-3 text-h3 font-semibold">बलियो र कमजोर पक्ष · Strengths and gaps</h3>
          <ul className="m-0 flex list-none flex-col gap-2 p-0">
            {ins.groups.map((g) => (
              <li key={g.name} className="grid grid-cols-[6.5rem_1fr_auto] items-center gap-3">
                <span className="font-story-ne text-small">{g.name}</span>
                <span className="h-2.5 overflow-hidden rounded-full bg-paper-sunken" aria-hidden>
                  <span className={`block h-full ${STATUS[g.status as keyof typeof STATUS].bar}`} style={{ width: `${(100 * g.mastered) / g.total}%` }} />
                </span>
                <span className="font-mono text-caption tabular-nums text-ink-2">
                  {g.mastered}/{g.total} · {STATUS[g.status as keyof typeof STATUS].en}
                  {g.practicing.length > 0 && ` · now: ${g.practicing.map(unitGlyph).join(' ')}`}
                </span>
              </li>
            ))}
          </ul>
        </div>

        <div className="flex flex-col gap-4">
          <div className="rounded-xl border-2 border-line bg-card p-4">
            <h3 className="m-0 mb-2 text-h3 font-semibold">गल्तीका ढाँचा · Mistake patterns</h3>
            {ins.patterns.length === 0 ? (
              <p className="m-0 text-small text-ink-3">No repeated pattern yet. Patterns appear after the same kind of mistake happens twice.</p>
            ) : (
              <ul className="m-0 flex list-none flex-col gap-2 p-0">
                {ins.patterns.map((x) => (
                  <li key={x.kind} className="text-small">
                    <span className="font-semibold">{x.label_en}</span> <span className="text-ink-3">· {x.count}×</span>
                    <div className="font-story-ne text-ink-2">{x.label_ne}</div>
                    {x.kind !== 'skipped_words' && (
                      <div className="font-mono text-caption text-ink-3">
                        {x.examples.map(([a, b]) => `${a}→${b}`).join('  ')}
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="rounded-xl border-2 border-line bg-card p-4">
            <h3 className="m-0 mb-2 text-h3 font-semibold">गति · Pace (14 days)</h3>
            <p className="m-0 font-mono text-small tabular-nums">
              {p.sessions_14d} sessions · {p.mastered_14d} letters mastered
              {p.wcpm_first != null && ` · ${p.wcpm_first} → ${p.wcpm_last} words/min`}
            </p>
            <p className="m-0 text-small text-ink-2">{TREND[p.trend as keyof typeof TREND]}</p>
          </div>
        </div>
      </div>
    </section>
  )
}
