import { AlertTriangle, ArrowLeft, Clock } from 'lucide-react'
import { useEffect, useState } from 'react'
import type { components } from '../api-types'
import { api, type Language } from '../api'
import { DotLoader } from '../components/DotLoader'
import { ContentControls } from '../components/ContentControls'
import { FamilyCode } from '../components/FamilyCode'
import { LevelStars, knownCount } from '../components/LevelStars'
import { MathsProgress } from '../components/MathsProgress'
import { ProfileInsights } from '../components/ProfileInsights'
import { UnitChip } from '../components/UnitChip'
import { unitGlyph } from '../units'

type Dashboard = components['schemas']['DashboardOut']
type Activities = components['schemas']['ActivitiesOut']

const LIMITS = [0, 10, 15, 20, 30] as const
const MATHS_LEVEL: Record<number, string> = { 1: 'adding up to 5', 2: 'adding and taking away up to 10', 3: 'adding and taking away up to 20' }
const glyph = unitGlyph // matras on a dotted circle: ◌ै

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border-2 border-b-4 border-line bg-card p-4">
      <div className="text-caption text-ink-3">{label}</div>
      <div className="font-mono text-stat font-medium tabular-nums">{value}</div>
    </div>
  )
}

// Parent view: plain language, bilingual, what to do next. No scores shown to the child.
export function ParentScreen({ learnerId, onBack }: { learnerId: string; onBack: () => void }) {
  const [d, setD] = useState<Dashboard | null>(null)
  const [lang, setLang] = useState<Language>('ne')
  const [acts, setActs] = useState<Activities | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [history, setHistory] = useState<components['schemas']['HistoryItemOut'][] | null>(null)

  useEffect(() => {
    api.dashboard(learnerId).then(setD).catch((e) => setError(String(e.message ?? e)))
    api.history(learnerId).then(setHistory).catch(() => {})
  }, [learnerId])

  useEffect(() => {
    setActs(null)
    api.activities(learnerId, lang).then(setActs).catch(() => {})
  }, [learnerId, lang])

  if (error) return <p className="p-8 text-omitted">{error}</p>
  if (!d) return <div className="p-8"><DotLoader /></div>

  const w = d.week[lang]
  const name = d.learner.name
  const story = lang === 'ne' ? 'font-story-ne' : 'font-story-en'

  return (
    <main className="mx-auto max-w-[960px] px-4 py-8 font-ui md:px-8">
      <button type="button" onClick={onBack} className="mb-6 flex items-center gap-2 text-body text-ink-2 hover:text-ink">
        <ArrowLeft size={20} strokeWidth={1.75} /> Learners
      </button>
      <h1 className="m-0 mb-1 text-display font-semibold">
        {name.ne} <span className="text-ink-3">· {name.en}</span>
      </h1>
      <p className="m-0 mb-3 text-body text-ink-3">अभिभावकका लागि · For parents: this week, what's hard, and how to help at home.</p>
      <ul className="m-0 mb-6 flex list-none flex-wrap gap-2 p-0 text-small">
        {(['ne', 'en'] as const).map((l) => (
          <li key={l} className="flex items-center gap-2 rounded-lg border border-line bg-card px-3 py-2">
            <span className="font-semibold">{l === 'ne' ? 'Nepali' : 'English'}:</span>
            <LevelStars level={d.learner.level[l] ?? 1} size={14} />
            <span>story level {d.learner.level[l] ?? 1} of 3 · {knownCount(d.learner, l)} {l === 'ne' ? 'letters' : 'sounds'} read confidently</span>
          </li>
        ))}
        {(['ne', 'en'] as const).map((l) => (
          <li key={`m${l}`} className="flex items-center gap-2 rounded-lg border border-line bg-card px-3 py-2">
            <span className="font-semibold">Maths ({l === 'ne' ? 'ने' : 'EN'}):</span>
            <LevelStars level={d.learner.maths_level[l] ?? 1} size={14} />
            <span>{MATHS_LEVEL[d.learner.maths_level[l] ?? 1]}</span>
          </li>
        ))}
      </ul>

      <div role="tablist" className="mb-6 flex gap-1">
        {(['ne', 'en'] as const).map((l) => (
          <button key={l} role="tab" aria-selected={lang === l} type="button" onClick={() => setLang(l)}
            className={`min-h-10 rounded-md px-4 text-body font-medium ${lang === l ? 'bg-primary-soft text-primary' : 'text-ink-2 hover:bg-paper-sunken'}`}>
            {l === 'ne' ? 'नेपाली पढाइ' : 'English reading'}
          </button>
        ))}
      </div>

      <ProfileInsights learnerId={learnerId} lang={lang} />

      {/* This week */}
      <h2 className="mb-3 text-h2 font-semibold">यो हप्ता · This week</h2>
      <div className="mb-3 grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="कथा · Stories" value={String(w.stories)} />
        <Stat label="पढेका शब्द · Words read" value={String(w.words_read)} />
        <Stat label="शुद्धता · Accuracy" value={w.mean_accuracy == null ? '—' : `${Math.round(w.mean_accuracy * 100)}%`} />
        <Stat label="शब्द/मिनेट · Words/min" value={w.mean_wcpm == null ? '—' : String(w.mean_wcpm)} />
      </div>
      <div className="mb-8 flex h-12 items-end gap-1" aria-label="Stories per day, last 7 days">
        {w.per_day.map((n, i) => (
          <div key={i} className="flex-1 rounded-t-sm bg-primary" style={{ height: `${Math.min(100, n * 25) || 4}%`, opacity: n ? 1 : 0.15 }} />
        ))}
      </div>

      {(w.mastered.length > 0 || w.introduced.length > 0) && (
        <section className="mb-8">
          <h2 className="mb-3 text-h2 font-semibold">सिकेका अक्षर · Learned</h2>
          <div className="flex flex-wrap gap-2">
            {w.mastered.map((u) => <UnitChip key={u} unit={u} state="mastered" lang={lang} changed="promoted" />)}
            {w.introduced.map((u) => <UnitChip key={u} unit={u} state="practicing" lang={lang} />)}
          </div>
          <p className="mt-2 text-small text-ink-3">Green: now reads it confidently. Amber: started learning it this week.</p>
        </section>
      )}

      {w.struggling.length > 0 && (
        <section className="mb-8 flex gap-3 rounded-xl border-2 border-substituted bg-substituted-soft p-4">
          <AlertTriangle className="shrink-0 text-substituted" size={24} />
          <div>
            <p className="m-0 font-semibold">
              {name.en} is finding {w.struggling.map(glyph).join(', ')} hard · {name.ne}लाई {w.struggling.map(glyph).join(', ')} गाह्रो भइरहेको छ
            </p>
            <p className="m-0 mt-1 text-small text-ink-2">
              Read wrong twice recently. Stories will keep practising it gently; the activities below help at home.
            </p>
          </div>
        </section>
      )}

      <MathsProgress learnerId={learnerId} lang={lang} name={name} />

      {/* Home activities */}
      <h2 className="mb-1 text-h2 font-semibold">घरमा अभ्यास · At home</h2>
      <p className="m-0 mb-3 text-small text-ink-3">
        Practising now: {(acts?.practicing ?? d.practicing[lang]).map(glyph).join(' ') || '—'}
      </p>
      {!acts ? (
        <div className="mb-8 flex items-center gap-3 text-small text-ink-3"><DotLoader /> preparing ideas…</div>
      ) : (
        <>
          {acts.practice_words.length > 0 && (
            <div className="mb-4">
              <p className="m-0 mb-2 text-small text-ink-2">Words {name.en} can read that practise these:</p>
              <div className={`flex flex-wrap gap-2 ${story} text-child-label`}>
                {acts.practice_words.map((x) => (
                  <span key={x} className="rounded-lg border-2 border-line bg-card px-3 py-1">{x}</span>
                ))}
              </div>
            </div>
          )}
          <div className="mb-8 grid gap-3 md:grid-cols-3">
            {acts.activities.map((a, i) => (
              <article key={i} className="rounded-xl border-2 border-b-4 border-line bg-card p-4">
                <h3 className="m-0 font-story-ne text-h3 font-semibold">{String(a.title_ne)}</h3>
                <p className="m-0 mb-2 text-small text-ink-3">{String(a.title_en)}</p>
                <p className="m-0 mb-2 font-story-ne text-body">{String(a.how_ne)}</p>
                <p className="m-0 mb-2 text-small text-ink-2">{String(a.how_en)}</p>
                {Array.isArray(a.child_words) && a.child_words.length > 0 && (
                  <p className={`m-0 ${story} text-body font-semibold`}>{(a.child_words as string[]).join(' · ')}</p>
                )}
              </article>
            ))}
          </div>
        </>
      )}

      <ContentControls learnerId={learnerId} initial={d.learner.controls} />
      <FamilyCode />

      {/* Time control */}
      <section className="mb-8 rounded-xl border-2 border-line bg-card p-4">
        <h2 className="m-0 mb-1 flex items-center gap-2 text-h2 font-semibold"><Clock size={20} /> दैनिक समय · Daily time</h2>
        <p className="m-0 mb-3 text-small text-ink-3">
          Used today: {d.used_today} min. When the limit is reached, {name.en} sees "see you tomorrow".
        </p>
        <div className="flex flex-wrap gap-2">
          {LIMITS.map((m) => (
            <button key={m} type="button" aria-pressed={d.daily_minutes === m}
              onClick={() => api.setDailyMinutes(learnerId, m).then(() => setD({ ...d, daily_minutes: m }))}
              className={`min-h-10 rounded-md border px-4 text-body ${d.daily_minutes === m ? 'border-primary bg-primary-soft text-primary' : 'border-line-strong hover:bg-paper-sunken'}`}>
              {m === 0 ? 'No limit' : `${m} min`}
            </button>
          ))}
        </div>
      </section>

      {/* Every story the child got: human-reviewable log, newest first */}
      {history && history.length > 0 && (
        <section>
          <h2 className="mb-3 text-h2 font-semibold">कथाहरू · Stories</h2>
          <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3">
            {history.map((h) => (
              <a key={h.story_id} href={`/parent/${learnerId}/story/${h.story_id}`}
                className="flex gap-3 rounded-xl border-2 border-b-4 border-line bg-card p-3 hover:bg-paper-sunken">
                <div className="size-16 shrink-0 overflow-hidden rounded-lg bg-paper-sunken">
                  {h.image_url && <img src={h.image_url} alt="" className="size-full object-cover" />}
                </div>
                <div className="min-w-0">
                  <div className={`truncate ${h.lang === 'ne' ? 'font-story-ne' : 'font-story-en'} text-body font-semibold`}>{h.title}</div>
                  <div className="font-mono text-caption text-ink-3 tabular-nums">
                    {new Date(h.at * 1000).toLocaleDateString()} · {h.lang === 'ne' ? 'ने' : 'EN'}
                  </div>
                  <div className="font-mono text-caption tabular-nums">
                    {h.accuracy != null ? `${Math.round(h.accuracy * 100)}% read` : h.read ? 'read' : 'not read yet'}
                  </div>
                </div>
              </a>
            ))}
          </div>
        </section>
      )}
    </main>
  )
}
