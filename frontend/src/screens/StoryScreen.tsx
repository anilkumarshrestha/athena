import { ArrowLeft, ArrowRight } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { api, type Language, type Story } from '../api'
import { RecordButton, StoryCard } from '../components/StoryCard'
import { VerifierLog } from '../components/VerifierLog'

const POLL_MS = 1500

export function StoryScreen({ learnerId, lang, onBack }: { learnerId: string; lang: Language; onBack: () => void }) {
  const [story, setStory] = useState<Story | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [showLog, setShowLog] = useState(false)
  const reqId = useRef(0)

  const load = useCallback(() => {
    const id = ++reqId.current
    setStory(null)
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

  return (
    <main className="mx-auto max-w-[784px] px-4 pb-16 pt-4 md:px-8">
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
          footer={
            <>
              <RecordButton disabled />
              {story && (
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

      {story && (
        <div className="mx-auto mt-8 max-w-[720px]">
          <button
            type="button"
            onClick={() => setShowLog((v) => !v)}
            className="mb-3 text-body text-ink-3 underline underline-offset-4 hover:text-ink-2"
          >
            {showLog ? 'Hide' : 'Show'} how this story was made
          </button>
          {showLog && <VerifierLog story={story} />}
        </div>
      )}
    </main>
  )
}
