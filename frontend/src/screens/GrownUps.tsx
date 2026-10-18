import { ArrowLeft, ChartColumn, GraduationCap } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api, type Learner } from '../api'
import { DotLoader } from '../components/DotLoader'
import { FamilyCode } from '../components/FamilyCode'
import { LevelStars, knownCount } from '../components/LevelStars'
import { accentOf, learns } from '../learner'

// For grown-ups (/grownups, behind the grown-up question): every child's parent view and
// teacher view in one place, plus the account (Google sign-in) and the family code. Kept off
// the children's screens so a child never wanders into them.

export function GrownUps({ onBack }: { onBack: () => void }) {
  const [learners, setLearners] = useState<Learner[] | null>(null)
  useEffect(() => {
    api.learners().then(setLearners).catch(() => setLearners([]))
  }, [])

  return (
    <main className="mx-auto max-w-[960px] px-4 py-8 font-ui md:px-8">
      <button type="button" onClick={onBack} className="mb-6 flex items-center gap-2 text-body text-ink-2 hover:text-ink">
        <ArrowLeft size={20} strokeWidth={1.75} /> Who's reading?
      </button>
      <h1 className="m-0 mb-1 text-display font-semibold">ठूला मान्छेका लागि · For grown-ups</h1>
      <p className="m-0 mb-6 text-body text-ink-3">How each child is doing, what to practise at home, and your account.</p>

      {!learners ? <DotLoader /> : (
        <ul className="m-0 mb-8 grid list-none gap-3 p-0">
          {learners.map((l) => (
            <li key={l.id} className="flex flex-wrap items-center gap-4 rounded-xl border-2 border-line bg-card p-4">
              <div className={`size-14 shrink-0 overflow-hidden rounded-full border-4 ${accentOf(l.id).ring}`}>
                <img src={l.avatar_url} alt="" className="size-full object-cover" onError={(e) => (e.currentTarget.style.visibility = 'hidden')} />
              </div>
              <div className="min-w-0 flex-1">
                <div className="text-h3 font-semibold">
                  <span className="font-story-ne">{l.name.ne}</span> <span className="text-ink-3">· {l.name.en}</span>
                  {l.profile.demo_copy && <span className="ml-2 rounded-full bg-paper-sunken px-2 py-0.5 text-caption text-ink-3">sample data</span>}
                </div>
                <div className="flex flex-wrap gap-x-4 text-small text-ink-2">
                  {(['ne', 'en'] as const).filter((x) => learns(l, x)).map((x) => (
                    <span key={x} className="inline-flex items-center gap-1">
                      {x === 'ne' ? 'Nepali' : 'English'} <LevelStars level={l.level[x] ?? 1} size={12} />
                      {knownCount(l, x)} {x === 'ne' ? 'letters' : 'sounds'}
                    </span>
                  ))}
                </div>
              </div>
              <div className="flex gap-2">
                <a href={`/parent/${l.id}`} className="flex min-h-11 items-center gap-2 rounded-lg border border-line-strong px-3 text-body hover:bg-paper-sunken">
                  <ChartColumn size={18} /> Parent view
                </a>
                <a href={`/mastery/${l.id}`} className="flex min-h-11 items-center gap-2 rounded-lg border border-line-strong px-3 text-body hover:bg-paper-sunken">
                  <GraduationCap size={18} /> Teacher view
                </a>
              </div>
            </li>
          ))}
        </ul>
      )}

      <FamilyCode />
    </main>
  )
}
