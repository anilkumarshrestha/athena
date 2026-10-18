import { AlertTriangle, Check, RotateCcw, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import type { components } from '../api-types'
import { api, type Language } from '../api'
import { DotLoader } from './DotLoader'
import { bi } from '../ui'

type Progress = components['schemas']['MathsProgressOut']
type Problem = components['schemas']['MathsProblemOut']

// Maths for adults (DESIGN.md §7): every number is computed in code from the child's taps.
// Parent: plain-language week + what to do at home. Teacher: adds every recent problem with the taps.
// Outcomes carry an icon and a word, never colour alone (§2).

const OP = {
  '+': { ne: 'जोड', en: 'Adding' },
  '-': { ne: 'घटाउ', en: 'Taking away' },
} as const

const MISTAKE = {
  off_by_one: {
    ne: 'गन्तीमा एकको फरक',
    en: 'Off by one when counting.',
    help: 'Count objects together, touching each one once.',
  },
  wrong_operation: {
    ne: 'घटाउनुपर्नेमा जोड्ने (वा उल्टो)',
    en: 'Added when the problem took away (or the other way).',
    help: 'Act it out with real things: "took away" means fewer are left.',
  },
} as const

// athena/maths.py LEVELS
const LEVEL = {
  1: { ne: 'जोड, ५ सम्म', en: 'adding up to 5' },
  2: { ne: 'जोड र घटाउ, १० सम्म', en: 'adding and taking away up to 10' },
  3: { ne: 'जोड र घटाउ, २० सम्म', en: 'adding and taking away up to 20' },
} as const

const pct = (x: number | null | undefined) => (x == null ? '—' : `${Math.round(x * 100)}%`)

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border-2 border-b-4 border-line bg-card p-4">
      <div className="text-caption text-ink-3">{label}</div>
      <div className="font-mono text-stat font-medium tabular-nums">{value}</div>
    </div>
  )
}

function Outcome({ p }: { p: Problem }) {
  if (!p.answers.length) return <span className="text-ink-3">— not answered</span>
  if (p.first_try)
    return <span className="inline-flex items-center gap-1 text-correct"><Check size={16} /> first try</span>
  if (p.solved)
    return <span className="inline-flex items-center gap-1 text-substituted"><RotateCcw size={16} /> on try {p.answers.indexOf(p.answer) + 1}</span>
  return <span className="inline-flex items-center gap-1 text-omitted"><X size={16} /> shown the answer</span>
}

export function MathsProgress({
  learnerId, lang, name, detail = false,
}: { learnerId: string; lang: Language; name: Record<string, string>; detail?: boolean }) {
  const [m, setM] = useState<Progress | null>(null)

  useEffect(() => {
    setM(null)
    api.mathsProgress(learnerId, lang).then(setM).catch(() => {})
  }, [learnerId, lang])

  const story = lang === 'ne' ? 'font-story-ne' : 'font-story-en'
  const mistakes = Object.entries(m?.mistakes ?? {}).filter(([k, n]) => n > 0 && k in MISTAKE) as [keyof typeof MISTAKE, number][]

  return (
    <section className="mb-8">
      <h2 className="mb-3 text-h2 font-semibold">{bi("गणित", "Maths")}</h2>
      {!m ? (
        <DotLoader />
      ) : m.total === 0 ? (
        <p className="m-0 text-small text-ink-3">No maths problems yet. They start from the maths button on the learner's screen.</p>
      ) : (
        <>
          <div className="mb-3 grid grid-cols-2 gap-3 md:grid-cols-4">
            <Stat label={bi("यो हप्ता", "This week")} value={String(m.week.problems)} />
            <Stat label={bi("पहिलो पटकमै", "First try")} value={pct(m.week.first_try)} />
            <Stat label={`${OP['+'].ne} · ${OP['+'].en}`} value={pct(m.by_op['+']?.first_try)} />
            <Stat label={`${OP['-'].ne} · ${OP['-'].en}`} value={m.by_op['-']?.problems ? pct(m.by_op['-'].first_try) : '—'} />
          </div>
          <p className="m-0 mb-1 text-body">
            <span className="font-mono tabular-nums">Level {m.level} / 3</span> · {LEVEL[m.level as 1 | 2 | 3]?.en} ·{' '}
            <span className="font-story-ne">{LEVEL[m.level as 1 | 2 | 3]?.ne}</span>
          </p>
          <p className="m-0 mb-4 text-small text-ink-3">
            The level rises after 4 of 5 right on the first try without a long wait, and steps back after 3 misses
            in a row. A right answer that took long counts as neither.
            First try: the share of problems answered right the first time.
            {m.largest_solved != null && ` Largest answer found on the first try: ${m.largest_solved}.`}
            {detail && ` All time: ${m.total} problems, ${pct(m.all_first_try)} first try.`}
            {m.cat_checks.judged > 0 && ` Checked the cat's answer correctly ${m.cat_checks.right} of ${m.cat_checks.judged} times.`}
          </p>

          {m.struggling.length > 0 && (
            <div className="mb-4 flex gap-3 rounded-xl border-2 border-substituted bg-substituted-soft p-4">
              <AlertTriangle className="shrink-0 text-substituted" size={24} />
              <p className="m-0 font-semibold">
                {name.en} is finding {m.struggling.map((o) => OP[o as '+' | '-'].en.toLowerCase()).join(' and ')} hard ·{' '}
                {name.ne}लाई {m.struggling.map((o) => OP[o as '+' | '-'].ne).join(' र ')} गाह्रो भइरहेको छ
              </p>
            </div>
          )}

          {mistakes.length > 0 && (
            <ul className="m-0 mb-4 grid list-none gap-2 p-0 md:grid-cols-2">
              {mistakes.map(([k, n]) => (
                <li key={k} className="rounded-xl border-2 border-line bg-card p-4">
                  <p className="m-0 font-story-ne text-body font-semibold">{MISTAKE[k].ne} <span className="font-mono text-ink-3">×{n}</span></p>
                  <p className="m-0 text-small text-ink-2">{MISTAKE[k].en}</p>
                  <p className="m-0 mt-1 text-small">{MISTAKE[k].help}</p>
                </li>
              ))}
            </ul>
          )}

          {detail && (
            <div className="overflow-x-auto rounded-md border border-line bg-card">
              <table className="w-full text-left text-small">
                <thead className="text-caption text-ink-3">
                  <tr>
                    <th className="p-3 font-medium">Problem</th>
                    <th className="p-3 font-medium">Sum</th>
                    <th className="p-3 font-medium">Taps</th>
                    <th className="p-3 font-medium">Time</th>
                    <th className="p-3 font-medium">Outcome</th>
                  </tr>
                </thead>
                <tbody>
                  {m.recent.map((p) => (
                    <tr key={p.id} className="border-t border-line align-top">
                      <td className={`p-3 ${story} text-body`}>{p.sentences.join(' ')}</td>
                      <td className="whitespace-nowrap p-3 font-mono tabular-nums">{p.a} {p.op} {p.b} = {p.answer}</td>
                      <td className="whitespace-nowrap p-3 font-mono tabular-nums">{p.answers.join(' → ') || '—'}</td>
                      <td className="whitespace-nowrap p-3 font-mono tabular-nums">{p.secs != null ? `${Math.round(p.secs)} s` : '—'}</td>
                      <td className="whitespace-nowrap p-3"><Outcome p={p} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </section>
  )
}
