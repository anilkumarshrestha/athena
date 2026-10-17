import { ArrowLeft } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api, type Language, type Learner } from '../api'
import { DotLoader } from '../components/DotLoader'
import { MasteryGrid } from '../components/MasteryGrid'

// Adult view (DESIGN.md §7 "Mastery"): the learner's units per language.
export function MasteryScreen({ learnerId, onBack }: { learnerId: string; onBack: () => void }) {
  const [learner, setLearner] = useState<Learner | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [lang, setLang] = useState<Language>('ne')

  useEffect(() => {
    api.learner(learnerId).then(setLearner).catch((e) => setError(String(e.message ?? e)))
  }, [learnerId])

  const units = learner?.units[lang] ?? []
  const mastered = units.filter((u) => u.state === 'mastered').map((u) => u.unit)
  const practicing = units.filter((u) => u.state === 'practicing').map((u) => u.unit)
  const resting = units.filter((u) => u.cooldown > 0).map((u) => u.unit)

  return (
    <main className="mx-auto max-w-[1200px] px-4 py-8 font-ui md:px-8">
      <button
        type="button"
        onClick={onBack}
        className="mb-6 flex items-center gap-2 text-body text-ink-2 hover:text-ink"
      >
        <ArrowLeft size={20} strokeWidth={1.75} /> Learners
      </button>

      {error && <p className="text-omitted">{error}</p>}
      {!learner && !error && <DotLoader />}

      {learner && (
        <>
          <h1 className="m-0 mb-1 text-display font-semibold">
            {learner.name.ne} <span className="text-ink-3">· {learner.name.en}</span>
          </h1>
          <p className="m-0 mb-6 text-body text-ink-3">
            Stories use mastered and practising units only. A unit read wrong twice in one session goes back to
            practising and sits out the next story.
          </p>

          <div role="tablist" className="mb-6 flex gap-1">
            {(['ne', 'en'] as const).map((l) => (
              <button
                key={l}
                role="tab"
                aria-selected={lang === l}
                type="button"
                onClick={() => setLang(l)}
                className={`min-h-10 rounded-md px-4 text-body font-medium ${
                  lang === l ? 'bg-primary-soft text-primary' : 'text-ink-2 hover:bg-paper-sunken'
                }`}
              >
                {l === 'ne' ? 'नेपाली' : 'English'}
              </button>
            ))}
          </div>

          <div className="rounded-md border border-line bg-card p-4">
            <MasteryGrid lang={lang} mastered={mastered} practicing={practicing} />
          </div>

          {resting.length > 0 && (
            <p className="mt-4 font-mono text-mono text-ink-3">
              sitting out the next story: {resting.map((u) => u.slice(u.indexOf(':') + 1)).join(' ')}
            </p>
          )}
        </>
      )}
    </main>
  )
}
