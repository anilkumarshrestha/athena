import { ArrowLeft, ArrowRight } from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api, type CloseResult, type Language, type ReadResult, type Story } from '../api'
import { ReadingLog } from '../components/ReadingLog'
import { RecordButton, StoryCard } from '../components/StoryCard'
import { VerifierLog } from '../components/VerifierLog'
import { UnitChip } from '../components/UnitChip'
import type { Outcome } from '../components/WordToken'
import { useRecorder } from '../hooks/useRecorder'

const POLL_MS = 1500

export function StoryScreen({ learnerId, lang, onBack }: { learnerId: string; lang: Language; onBack: () => void }) {
  const [story, setStory] = useState<Story | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [showLog, setShowLog] = useState(false)
  const [reading, setReading] = useState<ReadResult | null>(null)
  const [closed, setClosed] = useState<CloseResult | null>(null)
  const [checking, setChecking] = useState(false)
  const recorder = useRecorder()
  const reqId = useRef(0)

  const load = useCallback(() => {
    const id = ++reqId.current
    setStory(null)
    setReading(null)
    setClosed(null)
    setError(null)
    api
      .startSession(learnerId, lang)
      .then((s) => id === reqId.current && setStory(s))
      .catch((e) => id === reqId.current && setError(String(e.message ?? e)))
  }, [learnerId, lang])

  useEffect(load, [load])

  // Image is generated in parallel; poll until it lands.
  useEffect(() => {
    if (!story || story.image_status !== 'pending') return
    const t = setTimeout(() => {
      api.story(story.id).then((s) => s.id === story.id && setStory(s)).catch(() => {})
    }, POLL_MS)
    return () => clearTimeout(t)
  }, [story])

  const outcomes = useMemo(
    () => (reading ? new Map(reading.words.map((w) => [w.index, w.outcome as Outcome])) : undefined),
    [reading],
  )

  const onRecord = async () => {
    if (!story) return
    if (recorder.state !== 'recording') {
      setReading(null)
      return recorder.start()
    }
    const { blob, durationS } = await recorder.stop()
    setChecking(true)
    try {
      setReading(await api.read(story.id, blob, durationS))
      // First reading of a story updates mastery once; later re-reads are practice only.
      if (!closed) setClosed(await api.closeSession(story.id))
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setChecking(false)
    }
  }

  return (
    <main className="mx-auto box-content max-w-story px-4 pb-16 pt-4 md:px-8">
      <button
        type="button"
        onClick={onBack}
        aria-label="Back"
        className="mb-4 flex size-16 items-center justify-center rounded-full text-ink-2 transition-colors duration-150 hover:bg-paper-sunken"
      >
        <ArrowLeft size={32} strokeWidth={1.75} />
      </button>

      {error ? (
        <p className="rounded-lg border border-line bg-card p-8 text-child-label text-omitted">{error}</p>
      ) : (
        <StoryCard
          lang={lang}
          title={story?.title}
          sentences={story?.sentences}
          imageUrl={story?.image_url}
          imageStatus={story?.image_status}
          display={story?.display}
          outcomes={outcomes}
          footer={
            <>
              <RecordButton
                state={checking ? 'checking' : recorder.state === 'recording' ? 'recording' : 'idle'}
                disabled={!story}
                onClick={onRecord}
              />
              {story && recorder.state !== 'recording' && !checking && (
                <button
                  type="button"
                  onClick={load}
                  className="absolute right-8 flex min-h-16 items-center gap-2 rounded-lg px-4 text-child-label font-semibold text-primary transition-colors duration-150 hover:bg-primary-soft"
                >
                  {lang === 'ne' ? 'अर्को' : 'Next'}
                  <ArrowRight size={32} strokeWidth={1.75} />
                </button>
              )}
            </>
          }
        />
      )}

      {closed && closed.changes.length > 0 && (
        <div className="mx-auto mt-6 flex max-w-story flex-wrap items-center gap-3 rounded-lg border border-line bg-card p-4">
          {closed.changes.map((c) => (
            <UnitChip
              key={c.unit}
              unit={c.unit}
              size="lg"
              lang={lang}
              state={c.after as 'mastered' | 'practicing'}
              changed={c.after === 'mastered' ? 'promoted' : 'demoted'}
            />
          ))}
        </div>
      )}

      {story && (
        <div className="mt-8">
          <button
            type="button"
            onClick={() => setShowLog((v) => !v)}
            className="mb-3 text-body text-ink-3 underline underline-offset-4 hover:text-ink-2"
          >
            {showLog ? 'Hide' : 'Show'} how this story was made
          </button>
          {showLog && (
            <div className="flex flex-col gap-3">
              {reading && <ReadingLog result={reading} />}
              <VerifierLog story={story} />
            </div>
          )}
          {recorder.error && <p className="mt-3 text-body text-omitted">Microphone: {recorder.error}</p>}
        </div>
      )}
    </main>
  )
}
