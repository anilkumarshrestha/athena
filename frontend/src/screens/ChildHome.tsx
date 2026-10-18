import { ArrowLeft, BookOpen, Calculator, Drum } from 'lucide-react'
import { useEffect, useState, type ReactNode } from 'react'
import { api, type Learner } from '../api'
import { DotLoader } from '../components/DotLoader'
import { LevelStars, knownCount, neNum } from '../components/LevelStars'
import { accentOf, buddyEn, buddyNe, gainedStar, goalOf, learns } from '../learner'
import { sfx } from '../sound'
import { bi, uiLang } from '../ui'

// One child's home (/child/<id>): only their things. Big picture tiles for each activity in
// the languages they learn, with their stars; today's goal; a star gained since last time is
// celebrated once. Every activity comes back here.

function Tile({ href, children, className = '' }: { href: string; children: ReactNode; className?: string }) {
  return (
    <a href={href}
      className={`flex min-h-28 flex-col items-center justify-center gap-2 rounded-2xl border-2 border-b-4 p-4 text-center transition-transform duration-150 active:translate-y-1 ${className}`}>
      {children}
    </a>
  )
}

export function ChildHome({ learnerId, onBack }: { learnerId: string; onBack: () => void }) {
  const [l, setL] = useState<Learner | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [newStar, setNewStar] = useState(false)

  useEffect(() => {
    api.warm(learnerId).catch(() => {}) // a story ready in each language before the child taps
    api
      .learner(learnerId)
      .then((x) => {
        setL(x)
        if (gainedStar(x)) {
          setNewStar(true)
          setTimeout(sfx.sparkle, 400)
        }
      })
      .catch((e) => setError(String(e.message ?? e)))
  }, [learnerId])

  if (error) return <p className="p-8 text-omitted">{error}</p>
  if (!l) return <div className="p-8"><DotLoader /></div>

  const a = accentOf(l.id)
  const goal = goalOf(l)
  const langs = (['ne', 'en'] as const).filter((x) => learns(l, x))

  return (
    <main className="mx-auto box-content max-w-story px-4 pb-16 pt-4 md:px-8">
      <header className="mb-6 flex items-center gap-3">
        <button type="button" onClick={onBack} aria-label="Who's reading?" className="flex size-16 shrink-0 items-center justify-center rounded-full text-ink-2 hover:bg-paper-sunken">
          <ArrowLeft size={32} strokeWidth={1.75} />
        </button>
        <div className={`size-20 shrink-0 overflow-hidden rounded-full border-4 bg-card ${a.ring}`}>
          <img src={l.avatar_url} alt="" className="size-full object-cover" onError={(e) => (e.currentTarget.style.visibility = 'hidden')} />
        </div>
        <div className="min-w-0 flex-1">
          <div className={`${uiLang() === 'en' || l.profile.languages === 'en' ? 'font-story-en' : 'font-story-ne'} text-child-title font-bold leading-tight`}>
            {uiLang() === 'en' || l.profile.languages === 'en' ? l.name.en : l.name.ne}
          </div>
          <div className="flex items-center gap-2" aria-label="Today's reading goal">
            <div className="h-3 flex-1 overflow-hidden rounded-full bg-line">
              <div className="h-full rounded-full bg-leaf" style={{ width: `${Math.min(100, (l.used_today / goal) * 100)}%` }} />
            </div>
            <span className="font-mono text-caption tabular-nums text-ink-2">
              {l.used_today >= goal ? '✓ ' : ''}{Math.min(l.used_today, goal)}/{goal} min
            </span>
          </div>
        </div>
      </header>

      {newStar && (
        <p className="m-0 mb-4 flex items-center justify-center gap-2 rounded-2xl bg-sun-soft px-4 py-3 text-child-label font-bold">
          <LevelStars level={1} size={20} /> {bi("नयाँ तारा!", "New star!")}
        </p>
      )}

      {/* reading: the biggest tiles */}
      <div className="mb-4 grid gap-4 sm:grid-cols-2">
        {langs.map((x) => (
          <Tile key={x} href={`/read/${l.id}/${x}`} className={`${a.btn} min-h-36`}>
            <BookOpen size={36} />
            <span className={`${x === 'ne' ? 'font-story-ne' : 'font-story-en'} text-child-title font-bold`}>{x === 'ne' ? 'नेपाली' : 'English'}</span>
            <span className="flex items-center gap-2 text-small font-semibold">
              <LevelStars level={l.level[x] ?? 1} size={16} className="rounded-full bg-card px-1.5 py-0.5" />
              {x === 'ne' ? `${neNum(knownCount(l, 'ne'))} अक्षर` : `${knownCount(l, 'en')} sounds`}
            </span>
          </Tile>
        ))}
      </div>

      {l.controls.maths !== false && (
        <div className="mb-4 grid grid-cols-2 gap-4">
          {langs.map((x) => (
            <Tile key={x} href={`/maths/${l.id}/${x}`} className="border-line-strong bg-card text-ink">
              <Calculator size={30} className="text-primary" />
              <span className={`${x === 'ne' ? 'font-story-ne' : 'font-story-en'} text-child-label font-bold`}>{x === 'ne' ? 'गणित' : 'Maths'}</span>
              <LevelStars level={l.maths_level[x] ?? 1} size={16} />
            </Tile>
          ))}
        </div>
      )}

      <div className="mb-4 grid grid-cols-2 gap-4">
        {langs.map((x) => (
          <Tile key={x} href={`/clap/${l.id}/${x}`} className="border-coral-edge bg-coral-soft text-ink">
            <Drum size={30} className="text-coral-edge" />
            <span className={`${x === 'ne' ? 'font-story-ne' : 'font-story-en'} text-child-label font-bold`}>{x === 'ne' ? 'शब्दमा ताली' : 'Clap the word'}</span>
          </Tile>
        ))}
      </div>

      {l.controls.teach !== false && (
        <div className="grid grid-cols-2 gap-4">
          {langs.map((x) => (
            <Tile key={x} href={`/teach/${l.id}/${x}`} className="border-sun-edge bg-sun-soft text-ink">
              <img src={`/api/pictures/ne/${buddyNe(l)}`} alt="" className="size-12 rounded-full object-cover" />
              <span className={`${x === 'ne' ? 'font-story-ne' : 'font-story-en'} text-body font-bold`}>
                {x === 'ne' ? `${buddyNe(l)}लाई सिकाऊ` : `Teach the ${buddyEn(l)}`}
              </span>
            </Tile>
          ))}
        </div>
      )}
    </main>
  )
}
