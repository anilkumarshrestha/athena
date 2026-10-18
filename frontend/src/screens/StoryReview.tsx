import { ArrowLeft } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import type { components } from '../api-types'
import { api } from '../api'
import { DotLoader } from '../components/DotLoader'
import { StoryCard } from '../components/StoryCard'
import type { Outcome } from '../components/WordToken'
import { unitGlyph } from '../units'

type Detail = components['schemas']['HistoryStoryOut']

// Parent review of one past story: the story as the child saw it, each word coloured
// by how they read it, what speech-to-text heard, and what the verifier did. No audio.
const WAYS: Record<string, string> = { hear: 'heard it', parts: 'saw its parts', picture: 'saw a picture' }

export function StoryReview({ learnerId, storyId, onBack }: { learnerId: string; storyId: string; onBack: () => void }) {
  const [d, setD] = useState<Detail | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.historyStory(learnerId, storyId).then(setD).catch((e) => setError(String(e.message ?? e)))
  }, [learnerId, storyId])

  const reading = d?.readings[d.readings.length - 1] as
    | { transcript: string; wcpm: number; words_correct: number; words: { index: number; expected: string; heard: string | null; outcome: string; error_units: string[] }[] }
    | undefined
  const outcomes = useMemo(
    () => (reading ? new Map(reading.words.map((w) => [w.index, w.outcome as Outcome])) : undefined),
    [reading],
  )

  if (error) return <p className="p-8 text-omitted">{error}</p>
  if (!d) return <div className="p-8"><DotLoader /></div>

  const errors = reading?.words.filter((w) => w.outcome === 'substituted' || w.outcome === 'omitted') ?? []
  const retries = d.attempts.length

  return (
    <main className="mx-auto box-content max-w-story px-4 py-8 font-ui md:px-8">
      <button type="button" onClick={onBack} className="mb-6 flex items-center gap-2 text-body text-ink-2 hover:text-ink">
        <ArrowLeft size={20} strokeWidth={1.75} /> Parent view
      </button>
      <p className="m-0 mb-4 font-mono text-mono text-ink-3 tabular-nums">
        {new Date(d.at * 1000).toLocaleString()} · level {d.level} · {d.theme}
      </p>

      <StoryCard
        lang={d.lang}
        title={d.title}
        sentences={d.sentences}
        display={d.display}
        imageUrl={d.image_url}
        imageStatus={d.image_url ? 'ready' : 'failed'}
        outcomes={outcomes}
        wordPractice={d.outcome === 'wordlist'}
      />

      <section className="mt-6 rounded-xl border-2 border-line bg-card p-4 font-mono text-mono">
        {reading ? (
          <>
            <div className="text-ink-2 tabular-nums">
              read {reading.words_correct}/{reading.words.length} words · {reading.wcpm} words/min
              {d.close ? ` · accuracy ${Math.round(Number(d.close.accuracy) * 100)}%` : ''}
            </div>
            <div className="mt-1 text-ink-3">heard: {reading.transcript || '(nothing)'}</div>
            {errors.length > 0 && (
              <div className="mt-2 text-substituted">
                hard words:{' '}
                {errors
                  .map((w) => `${w.expected}${w.heard ? `→${w.heard}` : ' (skipped)'}${w.error_units.length ? ` [${w.error_units.map(unitGlyph).join(' ')}]` : ''}`)
                  .join(' · ')}
              </div>
            )}
          </>
        ) : (
          <div className="text-ink-3">Not read aloud yet.</div>
        )}
        {d.reteach.length > 0 && (
          <div className="mt-2">
            <div className="text-ink-2">practice with the help card:</div>
            <ul className="m-0 list-none p-0">
              {(d.reteach as { word: string; styles: string[]; correct: boolean; trigger?: string }[]).map((r, i) => (
                <li key={i} className="text-ink-2">
                  {r.trigger && r.trigger !== 'tap' && (
                    <span className="text-ink-3">[opened by Athena: {r.trigger === 'repeat' ? 'same letter missed twice' : 'long pause, then a miss'}] </span>
                  )}
                  <span className={d.lang === 'ne' ? 'font-story-ne' : 'font-story-en'}>{r.word}</span>
                  {': '}
                  {r.styles.length ? r.styles.map((x) => WAYS[x] ?? x).join(' → ') : 'tried straight away'}
                  {' → '}
                  {r.correct ? '✓ read it' : '○ not yet'}
                </li>
              ))}
            </ul>
          </div>
        )}
        <div className="mt-2 text-ink-3">
          story checked by the verifier: {retries} {retries === 1 ? 'draft' : 'drafts'}, outcome {d.outcome}, 0 unreadable words shown
        </div>
      </section>
    </main>
  )
}
