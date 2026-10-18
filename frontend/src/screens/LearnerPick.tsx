import { Volume2, VolumeX } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api, type Language, type Learner } from '../api'
import { DotLoader } from '../components/DotLoader'
import { setSoundOn, sfx, soundOn } from '../sound'

// First grapheme, not first code unit: क्षितिज → क्षि, not क.
const segmenter = new Intl.Segmenter('ne', { granularity: 'grapheme' })
const initial = (s?: string) => (s ? segmenter.segment(s)[Symbol.iterator]().next().value?.segment : undefined)

// Decorative child accents, cycled by index. Full class strings so Tailwind sees them.
const ACCENTS = [
  { tile: 'bg-sky-soft border-sky', avatar: 'bg-sky text-on-primary', btn: 'bg-sky border-sky-edge text-on-primary' },
  { tile: 'bg-sun-soft border-sun', avatar: 'bg-sun text-on-sun', btn: 'bg-sun border-sun-edge text-on-sun' },
  { tile: 'bg-leaf-soft border-leaf', avatar: 'bg-leaf text-on-primary', btn: 'bg-leaf border-leaf-edge text-on-primary' },
  { tile: 'bg-coral-soft border-coral', avatar: 'bg-coral text-on-primary', btn: 'bg-coral border-coral-edge text-on-primary' },
] as const
const CHUNKY = 'min-h-16 flex-1 rounded-xl border-b-4 text-child-label font-bold transition-transform duration-150 active:translate-y-1 active:border-b-0'

export function LearnerPick({ onPick }: { onPick: (learnerId: string, lang: Language) => void }) {
  const [learners, setLearners] = useState<Learner[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [sound, setSound] = useState(soundOn())

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
        <button
          type="button"
          aria-pressed={sound}
          onClick={() => {
            setSoundOn(!sound)
            setSound(!sound)
            if (!sound) sfx.pop()
          }}
          className="ml-auto flex min-h-10 items-center gap-2 rounded-md px-3 text-body text-ink-2 hover:bg-paper-sunken"
        >
          {sound ? <Volume2 size={20} /> : <VolumeX size={20} />}
          {sound ? 'Sounds on' : 'Sounds off'}
        </button>
      </div>

      {error && <p className="text-omitted">{error}</p>}
      {!learners && !error && <DotLoader />}

      <div className="grid gap-6 sm:grid-cols-2">
        {learners?.map((l, i) => {
          const a = ACCENTS[i % ACCENTS.length]
          return (
          <div key={l.id} className={`rounded-xl border-2 p-6 ${a.tile}`}>
            <div className="mb-6 flex items-center gap-4">
              <div className={`flex size-30 shrink-0 items-center justify-center rounded-full font-story-ne text-story-xl ${a.avatar}`}>
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
                className={`${CHUNKY} font-story-ne ${a.btn}`}
              >
                नेपाली
              </button>
              <button
                type="button"
                onClick={() => onPick(l.id, 'en')}
                className={`${CHUNKY} font-story-en ${a.btn}`}
              >
                English
              </button>
            </div>
            {l.controls.maths !== false && (
            <div className="mt-3 flex gap-3">
              {(['ne', 'en'] as const).map((ml) => (
                <a
                  key={ml}
                  href={`#/maths/${l.id}/${ml}`}
                  className={`flex min-h-14 flex-1 items-center justify-center gap-2 rounded-xl border-2 border-b-4 border-line-strong bg-card ${ml === 'ne' ? 'font-story-ne' : 'font-story-en'} text-child-label font-bold text-ink transition-transform duration-150 active:translate-y-1`}
                >
                  {ml === 'ne' ? 'गणित' : 'Maths'} <span className="font-mono text-small font-semibold text-ink-3">{ml === 'ne' ? '१+२' : '1+2'}</span>
                </a>
              ))}
            </div>
            )}
            {l.controls.teach !== false && (
            <div className="mt-3 flex gap-3">
              {(['ne', 'en'] as const).map((ml) => (
                <a
                  key={ml}
                  href={`#/teach/${l.id}/${ml}`}
                  className={`flex min-h-14 flex-1 items-center justify-center gap-2 rounded-xl border-2 border-b-4 border-sun-edge bg-sun-soft ${ml === 'ne' ? 'font-story-ne' : 'font-story-en'} text-small font-bold text-ink transition-transform duration-150 active:translate-y-1`}
                >
                  <img src="/api/pictures/ne/बिरालो" alt="" className="size-8 rounded-full object-cover" />
                  {ml === 'ne' ? 'बिरालोलाई सिकाऊ' : 'Teach the cat'}
                </a>
              ))}
            </div>
            )}
            <div className="mt-4 flex flex-wrap gap-x-4 gap-y-1">
              <a href={`#/parent/${l.id}`} className="text-body text-ink-3 underline underline-offset-4 hover:text-ink-2">
                Parent view
              </a>
              <a href={`#/mastery/${l.id}`} className="text-body text-ink-3 underline underline-offset-4 hover:text-ink-2">
                Teacher view: mastery
              </a>
            </div>
          </div>
          )
        })}
        <a
          href="#/new"
          className="flex min-h-48 flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-primary bg-card text-primary transition-colors duration-150 hover:bg-primary-soft"
        >
          <span className="font-story-ne text-child-title font-bold">+ नयाँ साथी</span>
          <span className="text-body text-ink-3">Add a learner</span>
        </a>
      </div>
    </main>
  )
}
