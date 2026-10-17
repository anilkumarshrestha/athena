import { useEffect, useState } from 'react'
import { api, type Language, type Learner } from '../api'
import { DotLoader } from '../components/DotLoader'

// First grapheme, not first code unit: क्षितिज → क्षि, not क.
const segmenter = new Intl.Segmenter('ne', { granularity: 'grapheme' })
const initial = (s?: string) => (s ? segmenter.segment(s)[Symbol.iterator]().next().value?.segment : undefined)

export function LearnerPick({ onPick }: { onPick: (learnerId: string, lang: Language) => void }) {
  const [learners, setLearners] = useState<Learner[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.learners().then(setLearners).catch((e) => setError(String(e.message ?? e)))
  }, [])

  return (
    <main className="mx-auto box-content max-w-story px-4 py-12 md:px-8">
      <div className="mb-12 flex items-center gap-3">
        <svg viewBox="0 0 32 32" className="size-10" aria-hidden>
          <path d="M8 25 16 6l8 19M11.5 18h9" fill="none" className="stroke-crimson" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <span className="text-child-title font-semibold">Athena</span>
      </div>

      {error && <p className="text-omitted">{error}</p>}
      {!learners && !error && <DotLoader />}

      <div className="grid gap-6 sm:grid-cols-2">
        {learners?.map((l) => (
          <div key={l.id} className="rounded-lg border border-line bg-card p-6">
            <div className="mb-6 flex items-center gap-4">
              <div className="flex size-30 shrink-0 items-center justify-center rounded-lg bg-paper-sunken font-story-ne text-story-xl text-ink-2">
                {initial(l.name.ne)}
              </div>
              <div>
                <div className="font-story-ne text-child-title font-bold">{l.name.ne}</div>
                <div className="font-story-en text-child-label text-ink-2">{l.name.en}</div>
              </div>
            </div>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => onPick(l.id, 'ne')}
                className="min-h-16 flex-1 rounded-lg border border-line-strong bg-card font-story-ne text-child-label font-semibold transition-colors duration-150 hover:bg-primary-soft"
              >
                नेपाली
              </button>
              <button
                type="button"
                onClick={() => onPick(l.id, 'en')}
                className="min-h-16 flex-1 rounded-lg border border-line-strong bg-card font-story-en text-child-label font-semibold transition-colors duration-150 hover:bg-primary-soft"
              >
                English
              </button>
            </div>
            <a href={`#/mastery/${l.id}`} className="mt-4 inline-block text-body text-ink-3 underline underline-offset-4 hover:text-ink-2">
              Teacher view: mastery
            </a>
          </div>
        ))}
      </div>
    </main>
  )
}
