import { Volume2, VolumeX } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api, type Language, type Learner } from '../api'
import { DotLoader } from '../components/DotLoader'
import { LevelStars, knownCount, neNum } from '../components/LevelStars'
import { JoinFamily } from '../components/FamilyCode'
import { setSoundOn, sfx, soundOn } from '../sound'

// Decorative child accents, cycled by index. Full class strings so Tailwind sees them.
const ACCENTS = [
  { tile: 'bg-sky-soft border-sky', avatar: 'bg-sky text-on-primary', btn: 'bg-sky border-sky-edge text-on-primary' },
  { tile: 'bg-sun-soft border-sun', avatar: 'bg-sun text-on-sun', btn: 'bg-sun border-sun-edge text-on-sun' },
  { tile: 'bg-leaf-soft border-leaf', avatar: 'bg-leaf text-on-primary', btn: 'bg-leaf border-leaf-edge text-on-primary' },
  { tile: 'bg-coral-soft border-coral', avatar: 'bg-coral text-on-primary', btn: 'bg-coral border-coral-edge text-on-primary' },
] as const
const CHUNKY = 'min-h-16 flex-1 rounded-xl border-b-4 text-child-label font-bold transition-transform duration-150 active:translate-y-1 active:border-b-0'

const BUDDY_NE: Record<string, string> = { cat: 'बिरालो', dog: 'कुकुर', goat: 'बाख्रा', bird: 'चरा', rabbit: 'खरायो' }
const buddyNe = (l: Learner) => BUDDY_NE[l.profile.buddy ?? 'cat'] ?? 'बिरालो'
const goalOf = (l: Learner) => Number(l.profile.daily_goal ?? 10)
const learns = (l: Learner, lang: 'ne' | 'en') => (l.profile.languages ?? 'both') === 'both' || l.profile.languages === lang

// Stars last seen on this device, per child: a gained star is celebrated once.
const STARS_KEY = 'athena.stars'
function starsGained(ls: Learner[]): Set<string> {
  const now: Record<string, number> = {}
  for (const l of ls) now[l.id] = (l.level.ne ?? 1) + (l.level.en ?? 1) + (l.maths_level.ne ?? 1) + (l.maths_level.en ?? 1)
  try {
    const before = JSON.parse(localStorage.getItem(STARS_KEY) ?? '{}') as Record<string, number>
    localStorage.setItem(STARS_KEY, JSON.stringify(now))
    return new Set(ls.filter((l) => before[l.id] !== undefined && now[l.id] > before[l.id]).map((l) => l.id))
  } catch {
    return new Set() // storage blocked: no celebration, nothing else changes
  }
}

export function LearnerPick({ onPick }: { onPick: (learnerId: string, lang: Language) => void }) {
  const [learners, setLearners] = useState<Learner[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [sound, setSound] = useState(soundOn())
  const [newStar, setNewStar] = useState<Set<string>>(new Set())

  useEffect(() => {
    api
      .learners()
      .then((ls) => {
        setLearners(ls)
        const up = starsGained(ls)
        if (up.size) {
          setNewStar(up)
          setTimeout(sfx.sparkle, 400)
        }
      })
      .catch((e) => setError(String(e.message ?? e)))
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
              {/* the child's own cartoon picture: found without reading */}
              <div className={`size-30 shrink-0 overflow-hidden rounded-full border-4 border-card ${a.avatar}`}>
                <img src={l.avatar_url} alt="" className="size-full object-cover"
                  onError={(e) => (e.currentTarget.style.visibility = 'hidden')} />
              </div>
              <div className="min-w-0 flex-1">
                {newStar.has(l.id) && (
                  <span className="mb-1 inline-flex items-center gap-1 rounded-full bg-sun-soft px-2 py-0.5 text-small font-bold text-ink">
                    <LevelStars level={1} size={12} /> नयाँ तारा! · New star!
                  </span>
                )}
                <div className="font-story-ne text-child-title font-bold">{l.name.ne}</div>
                <div className="font-story-en text-child-label text-ink-2">{l.name.en}</div>
                {/* today's goal: minutes so far / goal, as a bar + numbers (not colour alone) */}
                <div className="mt-2 flex items-center gap-2" aria-label="Today's reading goal">
                  <div className="h-3 flex-1 overflow-hidden rounded-full bg-line">
                    <div className="h-full rounded-full bg-leaf" style={{ width: `${Math.min(100, (l.used_today / goalOf(l)) * 100)}%` }} />
                  </div>
                  <span className="font-mono text-caption tabular-nums text-ink-2">
                    {l.used_today >= goalOf(l) ? '✓ ' : ''}{Math.min(l.used_today, goalOf(l))}/{goalOf(l)} min
                  </span>
                </div>
              </div>
            </div>
            <div className="flex gap-3">
              {learns(l, 'ne') && <button
                type="button"
                onClick={() => onPick(l.id, 'ne')}
                className={`${CHUNKY} flex flex-col items-center justify-center py-2 font-story-ne ${a.btn}`}
              >
                नेपाली
                {/* growth, not a grade: story-size stars + letters read confidently */}
                <span className="flex items-center gap-2 text-small font-semibold">
                  <LevelStars level={l.level.ne ?? 1} size={14} className="rounded-full bg-card px-1.5 py-0.5" />
                  {neNum(knownCount(l, 'ne'))} अक्षर
                </span>
              </button>}
              {learns(l, 'en') && <button
                type="button"
                onClick={() => onPick(l.id, 'en')}
                className={`${CHUNKY} flex flex-col items-center justify-center py-2 font-story-en ${a.btn}`}
              >
                English
                <span className="flex items-center gap-2 text-small font-semibold">
                  <LevelStars level={l.level.en ?? 1} size={14} className="rounded-full bg-card px-1.5 py-0.5" />
                  {knownCount(l, 'en')} sounds
                </span>
              </button>}
            </div>
            {l.controls.maths !== false && (
            <div className="mt-3 flex gap-3">
              {(['ne', 'en'] as const).filter((ml) => learns(l, ml)).map((ml) => (
                <a
                  key={ml}
                  href={`/maths/${l.id}/${ml}`}
                  className={`flex min-h-14 flex-1 items-center justify-center gap-2 rounded-xl border-2 border-b-4 border-line-strong bg-card ${ml === 'ne' ? 'font-story-ne' : 'font-story-en'} text-child-label font-bold text-ink transition-transform duration-150 active:translate-y-1`}
                >
                  {ml === 'ne' ? 'गणित' : 'Maths'} <LevelStars level={l.maths_level[ml] ?? 1} size={14} />
                </a>
              ))}
            </div>
            )}
            {l.controls.teach !== false && (
            <div className="mt-3 flex gap-3">
              {(['ne', 'en'] as const).filter((ml) => learns(l, ml)).map((ml) => (
                <a
                  key={ml}
                  href={`/teach/${l.id}/${ml}`}
                  className={`flex min-h-14 flex-1 items-center justify-center gap-2 rounded-xl border-2 border-b-4 border-sun-edge bg-sun-soft ${ml === 'ne' ? 'font-story-ne' : 'font-story-en'} text-small font-bold text-ink transition-transform duration-150 active:translate-y-1`}
                >
                  <img src={`/api/pictures/ne/${buddyNe(l)}`} alt="" className="size-8 rounded-full object-cover" />
                  {ml === 'ne' ? `${buddyNe(l)}लाई सिकाऊ` : `Teach the ${l.profile.buddy ?? 'cat'}`}
                </a>
              ))}
            </div>
            )}
            <div className="mt-4 flex flex-wrap gap-x-4 gap-y-1">
              <a href={`/parent/${l.id}`} className="text-body text-ink-3 underline underline-offset-4 hover:text-ink-2">
                Parent view
              </a>
              <a href={`/mastery/${l.id}`} className="text-body text-ink-3 underline underline-offset-4 hover:text-ink-2">
                Teacher view: mastery
              </a>
            </div>
          </div>
          )
        })}
        <a
          href="/new"
          className="flex min-h-48 flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-primary bg-card text-primary transition-colors duration-150 hover:bg-primary-soft"
        >
          <span className="font-story-ne text-child-title font-bold">+ नयाँ साथी</span>
          <span className="text-body text-ink-3">Add a learner</span>
        </a>
      </div>
      <div className="mt-8 flex justify-center">
        <JoinFamily />
      </div>
    </main>
  )
}
