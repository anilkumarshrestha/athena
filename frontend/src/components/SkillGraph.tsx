import { ArrowRight, Check, CircleDashed, Lock, Play } from 'lucide-react'
import { useEffect, useState } from 'react'
import type { components } from '../api-types'
import { api, type Language } from '../api'
import { unitGlyph } from '../units'
import { DotLoader } from './DotLoader'
import { bi } from '../ui'

type Graph = components['schemas']['SkillGraphOut']
type Need = { unit: string; known: boolean }
type Row = { unit: string; needs: Need[] }
type MathsSkill = { id: string; label_en: string; label_ne: string; status: string; problems: number; first_try: number | null }

// Teacher view of the skill graph (athena/skills.py): what is introduced next, what waits
// on a prerequisite, and the maths chain. Status is always an icon + a word, not colour alone.

const STATUS: Record<string, { icon: typeof Check; word: string; cls: string }> = {
  mastered: { icon: Check, word: 'mastered', cls: 'border-correct text-correct' },
  learning: { icon: Play, word: 'learning', cls: 'border-substituted text-substituted' },
  ready: { icon: CircleDashed, word: 'ready', cls: 'border-line-strong text-ink-2' },
  locked: { icon: Lock, word: 'locked', cls: 'border-line text-ink-4' },
}

const need = (n: Need) => (n.unit === 'any consonant' ? 'a consonant' : unitGlyph(n.unit))

export function SkillGraph({ learnerId, lang }: { learnerId: string; lang: Language }) {
  const [g, setG] = useState<Graph | null>(null)

  useEffect(() => {
    setG(null)
    api.skills(learnerId, lang).then(setG).catch(() => {})
  }, [learnerId, lang])

  if (!g) return <DotLoader />
  const story = lang === 'ne' ? 'font-story-ne' : 'font-story-en'
  const row = (r: Row) => (
    <li key={r.unit} className="flex flex-wrap items-center gap-2">
      <span className={`${story} min-w-10 rounded-md border-2 border-line bg-card px-2 text-center text-child-label`}>{unitGlyph(r.unit)}</span>
      {r.needs.length > 0 && <span className="text-small text-ink-3">needs</span>}
      {r.needs.map((n) => (
        <span key={n.unit} className={`inline-flex items-center gap-1 text-small ${n.known ? 'text-correct' : 'text-ink-2'}`}>
          {n.known ? <Check size={14} /> : <CircleDashed size={14} />}
          <span className={story}>{need(n)}</span>
          <span className="text-ink-3">{n.known ? 'known' : 'not yet'}</span>
        </span>
      ))}
    </li>
  )

  return (
    <section>
      <h2 className="mb-1 text-h2 font-semibold">{bi("सीपको नक्सा", "Skill graph")}</h2>
      <p className="m-0 mb-4 text-small text-ink-3">
        A unit is introduced only when what it builds on is known: a conjunct needs both its letters, a long vowel sign its
        short one, a breathy letter its plain partner, an English sound like sh its letters.
      </p>
      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-md border border-line bg-card p-4">
          <h3 className="m-0 mb-2 text-h3 font-semibold">Next to introduce</h3>
          <ul className="m-0 grid list-none gap-2 p-0">{(g.next as Row[]).map(row)}</ul>
          {g.next.length === 0 && <p className="m-0 text-small text-ink-3">Nothing new right now.</p>}
        </div>
        <div className="rounded-md border border-line bg-card p-4">
          <h3 className="m-0 mb-2 text-h3 font-semibold">Waiting for a prerequisite</h3>
          <ul className="m-0 grid list-none gap-2 p-0">{(g.waiting as Row[]).slice(0, 8).map(row)}</ul>
          {g.waiting.length === 0 && <p className="m-0 text-small text-ink-3">None.</p>}
        </div>
      </div>

      <h3 className="mb-2 mt-6 text-h3 font-semibold">{bi("गणितको क्रम", "Maths path")}</h3>
      <ol className="m-0 flex list-none flex-wrap items-center gap-2 p-0">
        {(g.maths as MathsSkill[]).map((m, i) => {
          const st = STATUS[m.status] ?? STATUS.locked
          const Icon = st.icon
          return (
            <li key={m.id} className="flex items-center gap-2">
              {i > 0 && <ArrowRight size={16} className="text-ink-3" />}
              <span className={`flex flex-col rounded-md border-2 bg-card px-3 py-2 ${st.cls}`}>
                <span className="flex items-center gap-1 text-small font-semibold"><Icon size={14} /> {st.word}</span>
                <span className="text-small text-ink">{m.label_en}</span>
                <span className="font-story-ne text-small text-ink-2">{m.label_ne}</span>
                {m.problems > 0 && (
                  <span className="font-mono text-caption tabular-nums text-ink-3">
                    {m.problems} done{m.first_try != null ? ` · ${Math.round(m.first_try * 100)}% first try` : ''}
                  </span>
                )}
              </span>
            </li>
          )
        })}
      </ol>
    </section>
  )
}
