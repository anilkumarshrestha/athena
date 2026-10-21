import { Lock, Volume2, VolumeX } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api, type Learner } from '../api'
import { DotLoader } from '../components/DotLoader'
import { JoinFamily } from '../components/FamilyCode'
import { StageBadge } from '../components/StageBadge'
import { accentOf, goalOf, learns } from '../learner'
import { setSoundOn, sfx, soundOn } from '../sound'
import { UiLangSwitch } from '../components/UiLangSwitch'
import { uiLang } from '../ui'

// "Who's reading today?" (/app): one big tile per child, found by their picture without
// reading. A tap opens that child's own home (/child/<id>). Grown-up things (parent and
// teacher views, family code, account) live behind one "For grown-ups" button.

export function LearnerPick() {
  const [learners, setLearners] = useState<Learner[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [sound, setSound] = useState(soundOn())

  useEffect(() => {
    api.learners().then(setLearners).catch((e) => setError(String(e.message ?? e)))
  }, [])

  return (
    <main className="mx-auto box-content max-w-[960px] px-4 py-10 md:px-8">
      <header className="mb-8 flex flex-wrap items-center gap-3">
        <svg viewBox="0 0 32 32" className="size-10" aria-hidden>
          <path d="M8 25 16 6l8 19M11.5 18h9" fill="none" className="stroke-crimson" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <span className="text-child-title font-semibold">Athena</span>
        <div className="ml-auto flex flex-wrap items-center gap-2">
          <UiLangSwitch />
          <button
            type="button"
            aria-pressed={sound}
            onClick={() => {
              setSoundOn(!sound)
              setSound(!sound)
              if (!sound) sfx.pop()
            }}
            className="flex min-h-10 items-center gap-2 rounded-full px-3 text-body text-ink-2 hover:bg-paper-sunken"
          >
            {sound ? <Volume2 size={20} /> : <VolumeX size={20} />}
            {sound ? 'Sounds on' : 'Sounds off'}
          </button>
          <a href="/grownups" className="flex min-h-10 items-center gap-2 rounded-full border border-line-strong bg-card px-4 text-body text-ink-2 hover:bg-paper-sunken">
            <Lock size={16} /> For grown-ups
          </a>
        </div>
      </header>

      <h1 className="m-0 mb-6 font-story-ne text-child-title font-bold">
        {uiLang() === 'en' ? <span className="font-story-en">Who's reading today?</span> : <>आज को पढ्छ? <span className="font-story-en text-child-label font-semibold text-ink-3">· Who's reading today?</span></>}
      </h1>

      {error && <p className="text-omitted">{error}</p>}
      {!learners && !error && <DotLoader />}

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        {learners?.map((l) => {
          const a = accentOf(l.id)
          const goal = goalOf(l)
          return (
            <a key={l.id} href={`/child/${l.id}`}
              className={`flex flex-col items-center gap-2 rounded-2xl border-2 border-b-4 p-4 text-center transition-transform duration-150 active:translate-y-1 ${a.tile}`}>
              <div className={`size-28 overflow-hidden rounded-full border-4 bg-card ${a.ring}`}>
                <img src={l.avatar_url} alt="" className="size-full object-cover" onError={(e) => (e.currentTarget.style.visibility = 'hidden')} />
              </div>
              {/* the name the visitor reads first: English in the English interface or for an English-only child */}
              {uiLang() === 'en' || l.profile.languages === 'en' ? (
                <>
                  <span className="font-story-en text-child-title font-bold leading-tight">{l.name.en}</span>
                  <span className="-mt-2 font-story-ne text-body text-ink-2">{l.name.ne}</span>
                </>
              ) : (
                <>
                  <span className="font-story-ne text-child-title font-bold leading-tight">{l.name.ne}</span>
                  <span className="-mt-2 font-story-en text-body text-ink-2">{l.name.en}</span>
                </>
              )}
              <span className="flex flex-wrap justify-center gap-1">
                {(['ne', 'en'] as const).filter((x) => learns(l, x)).map((x) => (
                  <span key={x} className="inline-flex items-center gap-1 rounded-full bg-card px-2 py-0.5 text-caption font-semibold text-ink-2">
                    {x === 'ne' ? 'ने' : 'EN'} <StageBadge stage={l.stage[x]} lang={x} className="border-0 px-0 py-0" />
                  </span>
                ))}
              </span>
              {/* today's goal: bar + numbers (not colour alone) */}
              <span className="flex w-full items-center gap-2" aria-label="Today's reading goal">
                <span className="h-2.5 flex-1 overflow-hidden rounded-full bg-card">
                  <span className="block h-full rounded-full bg-leaf" style={{ width: `${Math.min(100, (l.used_today / goal) * 100)}%` }} />
                </span>
                <span className="font-mono text-caption tabular-nums text-ink-2">
                  {l.used_today >= goal ? '✓ ' : ''}{Math.min(l.used_today, goal)}/{goal}
                </span>
              </span>
            </a>
          )
        })}
        <a href="/new"
          className="flex min-h-48 flex-col items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-primary bg-card text-primary transition-colors duration-150 hover:bg-primary-soft">
          {uiLang() === 'en' ? (
            <span className="font-story-en text-child-title font-bold">+ Add a learner</span>
          ) : (
            <>
              <span className="font-story-ne text-child-title font-bold">+ नयाँ साथी</span>
              <span className="text-body text-ink-3">Add a learner</span>
            </>
          )}
        </a>
      </div>
      <div className="mt-10 flex justify-center">
        <JoinFamily />
      </div>
    </main>
  )
}
