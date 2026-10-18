import { ArrowLeft, Drum, Volume2 } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import type { components } from '../api-types'
import { api, type Language } from '../api'
import { DotLoader } from '../components/DotLoader'
import { jingle, sfx, soundOn } from '../sound'

type ClapWord = components['schemas']['ClapWordOut']

// Clap the beats (athena/clap.py): hear a word, tap the drum once per beat (सी·ता, rab·bit).
// A soft music bed plays underneath (Lyria, shipped). Code counts the taps; a miss is never
// "wrong": the beats light up one by one with a pop ("let's clap together"), then try again.

const IDLE_MS = 1400 // no tap for this long after the first: the child is done
const DEMO_MS = 650

export function ClapScreen({ learnerId, lang, onBack }: { learnerId: string; lang: Language; onBack: () => void }) {
  const [words, setWords] = useState<ClapWord[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [i, setI] = useState(0)
  const [taps, setTaps] = useState(0)
  const [state, setState] = useState<'listen' | 'tapping' | 'right' | 'together' | 'done'>('listen')
  const [lit, setLit] = useState(-1) // beat highlighted in the demo / after a right answer
  const [stars, setStars] = useState(0)
  const idle = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const bed = useRef<HTMLAudioElement | null>(null)
  const isNe = lang === 'ne'
  const font = isNe ? 'font-story-ne' : 'font-story-en'
  const w = words?.[i]

  useEffect(() => {
    api.clapRound(learnerId, lang).then(setWords).catch((e) => setError(String(e.message ?? e)))
  }, [learnerId, lang])

  // the music bed: quiet, looping, only with sounds on
  useEffect(() => {
    if (!soundOn()) return
    const a = new Audio('/music/clap_bed.mp3')
    a.loop = true
    a.volume = 0.22
    bed.current = a
    a.play().catch(() => {})
    return () => a.pause()
  }, [])

  const say = useCallback(() => {
    if (!w) return
    new Audio(api.clapAudioUrl(learnerId, lang, w.word)).play().catch(() => {})
  }, [w, learnerId, lang])

  useEffect(() => {
    if (!w) return
    setTaps(0)
    setLit(-1)
    setState('listen')
    const t = setTimeout(() => {
      say()
      setState('tapping')
    }, 300)
    return () => clearTimeout(t)
  }, [w, say])

  const lightBeats = (onEnd: () => void) => {
    if (!w) return
    w.beats.forEach((_, k) => setTimeout(() => (setLit(k), sfx.pop()), (k + 1) * DEMO_MS))
    setTimeout(onEnd, (w.beats.length + 1) * DEMO_MS + 300)
  }

  const check = (n: number) => {
    if (!w) return
    api.clapAnswer(learnerId, lang, w.word, n).catch(() => {})
    if (n === w.beats.length) {
      setState('right')
      setStars((s) => s + 1)
      sfx.chime()
      lightBeats(() => (i + 1 < (words?.length ?? 0) ? setI(i + 1) : finish()))
    } else {
      setState('together') // gentle: show the beats, then the child tries again
      lightBeats(() => {
        setTaps(0)
        setLit(-1)
        setState('tapping')
      })
    }
  }

  const finish = () => {
    setState('done')
    bed.current?.pause()
    jingle('star')
  }

  const tap = () => {
    if (state !== 'tapping' || !w) return
    const n = taps + 1
    setTaps(n)
    sfx.pop()
    clearTimeout(idle.current)
    idle.current = setTimeout(() => check(n), IDLE_MS)
  }

  return (
    <main className="mx-auto box-content max-w-story px-4 pb-16 pt-4 md:px-8">
      <button type="button" onClick={onBack} aria-label="Back" className="mb-4 flex size-16 items-center justify-center rounded-full text-ink-2 hover:bg-paper-sunken">
        <ArrowLeft size={32} strokeWidth={1.75} />
      </button>
      {error && <p className="text-omitted">{error}</p>}
      {!words && !error && <div className="flex justify-center p-12"><DotLoader /></div>}
      {words && words.length === 0 && (
        <p className={`rounded-2xl border-2 border-line bg-card p-8 ${font} text-child-label`}>
          {isNe ? 'अहिले ताली बजाउने शब्द छैनन्। पहिले केही अक्षर सिकौँ!' : 'No clapping words yet. Learn a few more letters first!'}
        </p>
      )}

      {state === 'done' ? (
        <section className="flex flex-col items-center gap-4 rounded-2xl border-2 border-b-4 border-line bg-card p-10 text-center">
          <Drum size={56} className="text-primary" />
          <p className={`m-0 ${font} text-child-title font-bold`}>{isNe ? 'धेरै राम्रो ताली!' : 'Great clapping!'}</p>
          <p className="m-0 text-child-label">{'⭐'.repeat(stars)}</p>
          <button type="button" onClick={onBack} className="min-h-16 rounded-xl border-b-4 border-primary-hover bg-primary px-8 text-child-label font-bold text-on-primary">
            {isNe ? 'सकियो' : 'Done'}
          </button>
        </section>
      ) : w ? (
        <article className="flex flex-col items-center gap-6 rounded-2xl border-2 border-b-4 border-line bg-card p-6 text-center">
          <p className="m-0 font-mono text-caption text-ink-3 tabular-nums">{i + 1} / {words?.length}</p>
          {w.picture_url && <img src={w.picture_url} alt="" className="size-32 rounded-2xl object-cover" onError={(e) => (e.currentTarget.style.visibility = 'hidden')} />}
          <div className={`flex items-center gap-3 ${font} text-story-lg font-bold`}>
            {state === 'right' || state === 'together' ? (
              w.beats.map((b, k) => (
                <span key={k} className={`rounded-xl px-3 py-1 transition-colors duration-150 ${k <= lit ? 'bg-sun text-on-sun' : 'bg-paper-sunken text-ink-2'}`}>{b}</span>
              ))
            ) : (
              <span>{w.word}</span>
            )}
            <button type="button" onClick={say} aria-label="Hear it" className="flex size-12 items-center justify-center rounded-full border-2 border-sky-edge bg-sky-soft text-ink">
              <Volume2 size={22} />
            </button>
          </div>

          {/* one dot per tap (shape, not colour alone) */}
          <div className="flex min-h-8 items-center gap-2" aria-live="polite" aria-label={`${taps} taps`}>
            {Array.from({ length: taps }, (_, k) => (
              <span key={k} className="size-6 rounded-full bg-primary" />
            ))}
          </div>

          <button type="button" onPointerDown={tap} disabled={state !== 'tapping'} aria-label={isNe ? 'ताली' : 'Clap'}
            className="flex size-44 items-center justify-center rounded-full border-4 border-b-8 border-coral-edge bg-coral text-on-primary transition-transform duration-75 active:translate-y-1 active:border-b-4 disabled:opacity-60">
            <Drum size={88} strokeWidth={1.5} />
          </button>

          <p className={`m-0 min-h-8 ${font} text-child-label font-semibold text-ink-2`}>
            {state === 'together' ? (isNe ? 'सँगै ताली बजाऔँ!' : "Let's clap together!")
              : state === 'right' ? (isNe ? 'ठ्याक्कै!' : 'Just right!')
              : isNe ? 'हरेक टुक्रामा एक पटक थिच।' : 'Tap once for each beat.'}
          </p>
        </article>
      ) : null}
    </main>
  )
}
