import { ArrowLeft } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api, type Language, type Learner } from '../api'
import { DotLoader } from '../components/DotLoader'
import { MasteryGrid } from '../components/MasteryGrid'
import { MathsProgress } from '../components/MathsProgress'
import { SkillGraph } from '../components/SkillGraph'

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
          {learner.profile.demo_copy && (
        <p className="m-0 mb-4 rounded-lg border border-line bg-paper-sunken px-3 py-2 text-small text-ink-2">
          Sample data: a made-up week so you can see what this view shows. Your own children start empty.
        </p>
      )}
          <p className="m-0 mb-6 text-body text-ink-3">
            Stories use mastered and practising units only. A unit read wrong twice in one session goes back to
            practising and sits out the next story. After two strong sessions (90%+) the level rises and new
            units are introduced: the ones that let the child read the most new words.
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

          <div className="mb-4 flex flex-wrap gap-6 font-mono text-mono text-ink-2 tabular-nums">
            <span>
              level <span className="text-stat font-medium text-ink">{learner.level[lang] ?? 1}</span> / 3
            </span>
            <span>
              maths level <span className="text-stat font-medium text-ink">{learner.maths_level[lang] ?? 1}</span> / 3
            </span>
            <span>
              last sessions:{' '}
              {(learner.recent_accuracy[lang] ?? []).length
                ? learner.recent_accuracy[lang].map((a) => `${Math.round(a * 100)}%`).join(' · ')
                : 'none yet'}
            </span>
          </div>

          <div className="rounded-md border border-line bg-card p-4">
            <MasteryGrid lang={lang} mastered={mastered} practicing={practicing} />
          </div>

          <div className="mt-8">
            <SkillGraph learnerId={learner.id} lang={lang} />
          </div>

          <div className="mt-8">
            <MathsProgress learnerId={learner.id} lang={lang} name={learner.name} detail />
          </div>

          <div className="mt-12 border-t border-line pt-6">
            <button
              type="button"
              onClick={async () => {
                if (!confirm(`Delete ${learner.name.en} and all their progress? This cannot be undone.`)) return
                await api.deleteLearner(learner.id)
                onBack()
              }}
              className="min-h-10 rounded-md border border-omitted px-4 text-body text-omitted hover:bg-omitted-soft"
            >
              Delete learner and their data
            </button>
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
