import { Mic, Square, Volume2, X } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import type { components } from '../api-types'
import { api, type Language } from '../api'
import { useRecorder } from '../hooks/useRecorder'
import { DotLoader } from './DotLoader'

type WordHelp = components['schemas']['WordHelpOut']

// Re-teach one word, three ways: hear it, see its parts (the tricky part marked),
// try again. Never "wrong": a miss just offers to listen again.

const chunky =
  'flex min-h-16 items-center justify-center gap-2 rounded-xl border-2 border-b-4 px-5 text-child-label font-bold transition-colors duration-150 active:translate-y-1 active:border-b-2'

export function ReteachPanel({
  storyId,
  index,
  lang,
  onClose,
  onSuccess,
}: {
  storyId: string
  index: number
  lang: Language
  onClose: () => void
  onSuccess: (index: number) => void
}) {
  const [help, setHelp] = useState<WordHelp | null>(null)
  const [retry, setRetry] = useState<'idle' | 'checking' | 'yes' | 'again'>('idle')
  const recorder = useRecorder()
  const audio = useRef<HTMLAudioElement | null>(null)
  const isNe = lang === 'ne'

  const hear = useCallback(() => {
    audio.current?.pause()
    audio.current = new Audio(api.wordAudioUrl(storyId, index))
    audio.current.play().catch(() => {})
  }, [storyId, index])

  useEffect(() => {
    api.wordHelp(storyId, index).then(setHelp).catch(() => {})
    hear() // hearing it is the first help
    return () => audio.current?.pause()
  }, [storyId, index, hear])

  const onRecord = async () => {
    if (recorder.state !== 'recording') {
      setRetry('idle')
      return recorder.start()
    }
    const { blob } = await recorder.stop()
    setRetry('checking')
    try {
      const r = await api.retryWord(storyId, index, blob)
      setRetry(r.correct ? 'yes' : 'again')
      if (r.correct) onSuccess(index)
    } catch {
      setRetry('again')
    }
  }

  const story = isNe ? 'font-story-ne' : 'font-story-en'

  return (
    <section
      aria-label="Word help"
      className="relative mx-auto mt-6 max-w-story rounded-2xl border-2 border-b-4 border-line bg-card p-6"
    >
      <button type="button" onClick={onClose} aria-label="Close" className="absolute right-3 top-3 flex size-12 items-center justify-center rounded-full text-ink-3 hover:bg-paper-sunken">
        <X size={24} strokeWidth={2} />
      </button>

      {!help ? (
        <DotLoader />
      ) : (
        <div className="flex flex-col items-center gap-6">
          <div className={`${story} text-story-xl font-semibold`}>{help.word}</div>

          {/* See its parts */}
          <div className="flex flex-wrap justify-center gap-2">
            {help.parts.map((p, i) => (
              <span
                key={i}
                className={`${story} flex min-h-16 min-w-16 items-center justify-center rounded-xl border-2 px-3 text-story-md ${
                  p.tricky ? 'border-substituted bg-substituted-soft text-ink' : 'border-line bg-paper text-ink-2'
                }`}
              >
                {p.text}
              </span>
            ))}
          </div>

          <div className="flex w-full flex-wrap justify-center gap-3">
            <button type="button" onClick={hear} className={`${chunky} border-line-strong bg-card text-ink-2 hover:bg-paper-sunken`}>
              <Volume2 size={26} strokeWidth={2} />
              {isNe ? 'सुन' : 'Hear'}
            </button>
            <button
              type="button"
              onClick={onRecord}
              disabled={retry === 'checking'}
              className={`${chunky} border-primary-hover bg-primary text-on-primary hover:bg-primary-hover disabled:bg-ink-4`}
              style={recorder.state === 'recording' ? { animation: 'ring-pulse 1.6s ease-in-out infinite' } : undefined}
            >
              {recorder.state === 'recording' ? <Square size={22} fill="currentColor" /> : <Mic size={26} strokeWidth={2} />}
              {recorder.state === 'recording' ? (isNe ? 'रोक' : 'Stop') : isNe ? 'फेरि पढ' : 'Try again'}
            </button>
          </div>

          <div aria-live="polite" className="min-h-8 text-child-label font-semibold">
            {retry === 'checking' && <DotLoader label="Checking" />}
            {retry === 'yes' && <span className="text-selfcorrected">✓ {isNe ? 'राम्रो!' : 'Well done!'}</span>}
            {retry === 'again' && (
              <span className="text-ink-2">{isNe ? 'फेरि सुनौँ, अनि पढौँ।' : "Let's listen once more."}</span>
            )}
          </div>
        </div>
      )}
    </section>
  )
}
