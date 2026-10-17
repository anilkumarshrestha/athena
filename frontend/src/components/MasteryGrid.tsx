import type { Language } from '../api'
import { chartRows, KIND_LABEL, type UnitState } from '../units'
import { UnitChip } from './UnitChip'

// DESIGN.md §6.3: the learner's mastery set laid out like the classroom
// varnamala chart (Nepali) or the phonics sequence (English).

const LEGEND: UnitState[] = ['mastered', 'practicing', 'unseen', 'excluded']

export function MasteryGrid({
  lang,
  mastered,
  practicing = [],
  excluded = [],
  changed = {},
  size = 'sm',
}: {
  lang: Language
  mastered: string[]
  practicing?: string[]
  excluded?: string[]
  changed?: Record<string, 'promoted' | 'demoted'>
  size?: 'sm' | 'lg'
}) {
  const m = new Set(mastered)
  const p = new Set(practicing)
  const x = new Set(excluded)
  const stateOf = (u: string): UnitState => (x.has(u) ? 'excluded' : p.has(u) ? 'practicing' : m.has(u) ? 'mastered' : 'unseen')

  // The child sees letters only; matras, conjuncts and tricky words stay on the adult view.
  const rows = chartRows(lang, [...m, ...p, ...x]).filter((r) => size === 'sm' || r.childVisible)

  // "31 / 33 letters" per kind, counted over what the chart shows.
  const totals = new Map<string, [number, number]>()
  for (const u of rows.flatMap((r) => r.units)) {
    const k = u.slice(0, 2)
    const [have, all] = totals.get(k) ?? [0, 0]
    totals.set(k, [have + (stateOf(u) === 'mastered' ? 1 : 0), all + 1])
  }

  return (
    <section className={size === 'sm' ? 'font-ui text-body' : ''}>
      {size === 'sm' && (
        <header className="mb-4 flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap gap-x-4 gap-y-1 font-mono text-mono text-ink-2 tabular-nums">
            {[...totals].map(([k, [have, all]]) => (
              <span key={k}>
                {have} / {all} {KIND_LABEL[k]}
              </span>
            ))}
          </div>
          <ul className="m-0 flex list-none flex-wrap gap-3 p-0 text-caption text-ink-3">
            {LEGEND.map((s) => (
              <li key={s} className="flex items-center gap-1.5">
                <span
                  aria-hidden
                  className={`relative inline-block size-3.5 rounded-sm border-2 ${
                    s === 'mastered'
                      ? 'border-correct bg-correct'
                      : s === 'practicing'
                        ? 'border-substituted bg-substituted-soft'
                        : s === 'unseen'
                          ? 'border-dashed border-line-strong'
                          : 'border-line bg-paper-sunken'
                  }`}
                />
                {s}
              </li>
            ))}
          </ul>
        </header>
      )}

      <div className={`flex flex-col ${size === 'sm' ? 'gap-2' : 'gap-3'}`}>
        {rows.map((r) => (
          <div key={r.label} className="flex items-center gap-4">
            {size === 'sm' && <div className="w-24 shrink-0 text-caption text-ink-3">{r.label}</div>}
            <div className={`flex flex-wrap ${size === 'sm' ? 'gap-1' : 'gap-3'}`}>
              {r.units.map((u) => (
                <UnitChip key={u} unit={u} state={stateOf(u)} size={size} lang={lang} changed={changed[u]} />
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
