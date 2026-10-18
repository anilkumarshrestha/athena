import { Mic, Shuffle, Square, Volume2, X } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import type { components } from '../api-types'
import { api, type Language } from '../api'
import { useRecorder } from '../hooks/useRecorder'
import { sfx } from '../sound'
import { DotLoader } from './DotLoader'

type WordHelp = components['schemas']['WordHelpOut']

// Re-teach one word, one way at a time: hear it, see its parts (the tricky part marked),
// see a picture (concrete nouns). The way that has worked best for this child comes first
// (athena/reteach.py); "another way" shows the next. Every retry logs the ways used, so the
// card keeps learning the child. Never "wrong": a miss just offers another way.

const chunky =
  'flex min-h-14 items-center justify-center gap-2 rounded-xl border-2 border-b-4 px-4 text-child-label font-bold transition-colors duration-150 active:translate-y-1 active:border-b-2'

export function ReteachPanel({
  storyId,
  index,
  lang,
  onClose,
  onSuccess,
  trigger = 'tap',
}: {
  storyId: string
  index: number
  lang: Language
  onClose: () => void
  onSuccess: (index: number) => void
  trigger?: 'tap' | 'repeat' | 'pause' // repeat/pause: Athena opened the card after the reading
}) {
  const [help, setHelp] = useState<WordHelp | null>(null)
  const [retry, setRetry] = useState<'idle' | 'checking' | 'yes' | 'again'>('idle')
  const [pic, setPic] = useState<'loading' | 'ready' | 'none'>('loading')
  const [shown, setShown] = useState(1) // how many ways are open, in the child's best order
  const used = useRef<string[]>([]) // ways used before the next retry, in order (logged)
  const recorder = useRecorder()
  const audio = useRef<HTMLAudioElement | null>(null)
  const isNe = lang === 'ne'

  // "ख, खसीको ख": the tricky letter tied to a familiar word, said as a teacher would
  const sayAnchor = (k: number) => {
    if (used.current[used.current.length - 1] !== 'anchor') used.current.push('anchor')
    audio.current?.pause()
    audio.current = new Audio(api.anchorAudioUrl(storyId, index, k))
    audio.current.play().catch(() => {})
  }

  const markUsed = (style: string) => {
    if (used.current[used.current.length - 1] !== style) used.current.push(style)
  }

  const hear = useCallback(() => {
    if (used.current[used.current.length - 1] !== 'hear') used.current.push('hear')
    audio.current?.pause()
    audio.current = new Audio(api.wordAudioUrl(storyId, index))
    audio.current.play().catch(() => {})
  }, [storyId, index])

  useEffect(() => {
    used.current = []
    setShown(1)
    api
      .wordHelp(storyId, index)
      .then((h) => {
        setHelp(h)
        const first = h.styles[0] ?? 'hear'
        if (first === 'hear') hear() // hearing it is this child's best first help
        else if (first === 'anchor') sayAnchor(0)
        else markUsed(first)
      })
      .catch(() => {})
    return () => audio.current?.pause()
  }, [storyId, index, hear])

  const open = help ? help.styles.slice(0, shown) : []
  const another = () => {
    if (!help || shown >= help.styles.length) return
    const next = help.styles[shown]
    setShown(shown + 1)
    if (next === 'hear') hear()
    else if (next === 'anchor') sayAnchor(0)
    else markUsed(next)
  }

  const onRecord = async () => {
    if (recorder.state !== 'recording') {
      setRetry('idle')
      return recorder.start()
    }
    const { blob } = await recorder.stop()
    setRetry('checking')
    try {
      const r = await api.retryWord(storyId, index, blob, used.current, trigger)
      used.current = [] // the next try is credited to whatever is used after this one
      setRetry(r.correct ? 'yes' : 'again')
      if (r.correct) sfx.chime() // a miss stays silent
      if (r.correct) onSuccess(index)
    } catch {
      setRetry('again')
    }
  }

  const story = isNe ? 'font-story-ne' : 'font-story-en'

  return (
    <div className="relative">
      <button type="button" onClick={onClose} aria-label="Close" className="absolute -right-2 -top-2 flex size-10 items-center justify-center rounded-full text-ink-3 hover:bg-paper-sunken">
        <X size={22} strokeWidth={2} />
      </button>

      {!help ? (
        <DotLoader />
      ) : (
        <div className="flex flex-col items-center gap-4">
          {trigger !== 'tap' && (
            <p className={`m-0 ${isNe ? 'font-story-ne' : 'font-story-en'} text-child-label font-semibold text-ink-2`}>
              {isNe ? 'यो शब्द सँगै हेरौँ।' : "Let's look at this word together."}
            </p>
          )}
          {/* See it: a picture for concrete nouns (cached per word) */}
          {open.includes('picture') && help.picture_url && pic !== 'none' && (
            <div className="flex size-28 items-center justify-center overflow-hidden rounded-2xl border-2 border-line bg-paper-sunken">
              {pic === 'loading' && <DotLoader label="Drawing" />}
              <img
                src={help.picture_url}
                alt=""
                onLoad={() => setPic('ready')}
                onError={() => setPic('none')}
                className={pic === 'ready' ? 'size-full object-cover' : 'hidden'}
              />
            </div>
          )}
          <div className={`${story} text-story-lg font-semibold`}>{help.word}</div>

          {/* Tie the tricky letter to a word the child knows */}
          {open.includes('anchor') && help.anchors.length > 0 && (
            <div className="flex flex-wrap justify-center gap-3">
              {help.anchors.map((a, k) => (
                <button key={a.glyph} type="button" onClick={() => sayAnchor(k)}
                  className={`${story} flex min-h-14 items-center gap-3 rounded-xl border-2 border-b-4 border-sun-edge bg-sun-soft px-4 text-child-label active:translate-y-1`}>
                  <span className="text-story-md font-bold">{a.glyph}</span>
                  <span aria-hidden className="text-ink-3">→</span>
                  {a.picture_url && <img src={a.picture_url} alt="" className="size-10 rounded-lg object-cover" />}
                  <span className="font-semibold">{a.word}</span>
                  <Volume2 size={22} className="text-ink-2" />
                </button>
              ))}
            </div>
          )}

          {/* See its parts */}
          {open.includes('parts') && (
          <div className="flex flex-wrap justify-center gap-2">
            {help.parts.map((p, i) => (
              <span
                key={i}
                className={`${story} flex min-h-12 min-w-12 items-center justify-center rounded-lg border-2 px-2 text-child-label ${
                  p.tricky ? 'border-substituted bg-substituted-soft text-ink' : 'border-line bg-paper text-ink-2'
                }`}
              >
                {p.text}
              </span>
            ))}
          </div>
          )}

          <div className="flex w-full flex-wrap justify-center gap-2">
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
              <span className="text-ink-2">{isNe ? 'अर्को तरिकाले हेरौँ।' : "Let's try another way."}</span>
            )}
          </div>

          {shown < help.styles.length && (
            <button type="button" onClick={another} className={`${chunky} border-sky-edge bg-sky-soft text-ink`}>
              <Shuffle size={24} strokeWidth={2} />
              {isNe ? 'अर्को तरिका' : 'Another way'}
            </button>
          )}
        </div>
      )}
    </div>
  )
}
