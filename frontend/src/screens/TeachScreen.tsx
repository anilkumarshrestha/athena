import { ArrowLeft, ArrowRight, Eye, Moon, Volume2 } from 'lucide-react'
import { Fragment, useCallback, useEffect, useRef, useState } from 'react'
import type { components } from '../api-types'
import { api, type Language } from '../api'
import { DotLoader } from '../components/DotLoader'
import { WordToken } from '../components/WordToken'
import { jingle, sfx } from '../sound'

type Teach = components['schemas']['TeachOut']

// Teach the buddy (athena/teach.py): the cat reads a story the child already read, with a few
// words wrong, chosen in code from this child's own confusions. The child points them out
// and hears each word said properly. The child is the teacher; nothing here is ever "wrong".

const T = {
  ne: {
    hello: 'म यो कथा पढ्छु। मेरो गल्ती समात्न सक्छौ?',
    read: (b: string) => `${b} पढ्छ`,
    found: (n: number, of: number) => `${n}/${of} गल्ती भेटियो`,
    thanks: (w: string) => `धन्यवाद! यो "${w}" हो।`,
    notThis: 'यो त मैले ठीक पढेँ जस्तो लाग्छ। फेरि सुन!',
    showMe: 'मलाई देखाऊ',
    done: 'तिमी राम्रो शिक्षक हौ!',
    again: 'फेरि सिकाऊ',
    first: (b: string) => `पहिले एउटा कथा पढ, अनि ${b}लाई सिकाउन आऊ।`,
    limit: 'आजलाई यति नै! भोलि फेरि खेलौँ।',
  },
  en: {
    hello: "I'll read this story. Can you catch my mistakes?",
    read: (b: string) => `${b} reads`,
    found: (n: number, of: number) => `${n} of ${of} mistakes found`,
    thanks: (w: string) => `Thank you! It's "${w}".`,
    notThis: 'I think I read that one right. Listen again!',
    showMe: 'Show me',
    done: "You're a great teacher!",
    again: 'Teach again',
    first: (b: string) => `Read a story first, then come and teach the ${b}.`,
    limit: "That's all for today. Let's play again tomorrow!",
  },
} as const

export function TeachScreen({ learnerId, lang, onBack }: { learnerId: string; lang: Language; onBack: () => void }) {
  const [t, setT] = useState<Teach | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [found, setFound] = useState<number[]>([])
  const [shown, setShown] = useState<number[]>([]) // revealed by "show me"
  const [say, setSay] = useState<string>('')
  const [misses, setMisses] = useState(0)
  const [playing, setPlaying] = useState(false)
  const audio = useRef<HTMLAudioElement | null>(null)
  const tx = T[lang]
  const buddy = lang === 'ne' ? (t?.buddy_ne ?? 'साथी') : (t?.buddy_en ?? 'buddy')
  const font = lang === 'ne' ? 'font-story-ne' : 'font-story-en'

  const load = useCallback(() => {
    setT(null)
    setError(null)
    setFound([])
    setShown([])
    setMisses(0)
    setSay('')
    api.teachStart(learnerId, lang).then(setT).catch((e) => setError(String(e.message ?? e)))
  }, [learnerId, lang])
  useEffect(load, [load])
  useEffect(() => () => audio.current?.pause(), [])

  const play = (url: string) => {
    audio.current?.pause()
    const a = new Audio(url)
    audio.current = a
    setPlaying(true)
    a.onended = () => setPlaying(false)
    a.play().catch(() => setPlaying(false))
  }

  const done = t != null && found.length >= t.mistakes

  const tap = async (index: number) => {
    if (!t || done || found.includes(index)) return
    const r = await api.teachTap(t.id, index)
    if (r.caught) {
      setFound(r.found)
      setSay(tx.thanks(r.word ?? ''))
      sfx.chime()
      setTimeout(() => play(api.teachWordAudioUrl(t.id, index)), 300) // the word, said properly
      if (r.left === 0) setTimeout(() => jingle('cat'), 1400) // all the cat's mistakes caught
    } else {
      setMisses((m) => m + 1)
      setSay(tx.notThis) // gentle, silent: no "wrong" sound
    }
  }

  return (
    <main className="mx-auto box-content max-w-story px-4 pb-16 pt-4 md:px-8">
      <button type="button" onClick={onBack} aria-label="Back" className="mb-4 flex size-16 items-center justify-center rounded-full text-ink-2 hover:bg-paper-sunken">
        <ArrowLeft size={32} strokeWidth={1.75} />
      </button>

      {error === 'daily_limit' ? (
        <section className="flex flex-col items-center gap-4 rounded-2xl border-2 border-b-4 border-line bg-card p-12 text-center">
          <Moon size={64} strokeWidth={1.5} className="text-primary" />
          <p className={`m-0 ${font} text-child-title font-bold`}>{tx.limit}</p>
        </section>
      ) : error ? (
        <p className={`rounded-2xl border-2 border-line bg-card p-8 ${font} text-child-label text-ink-2`}>
          {error.startsWith('read a story') ? tx.first(buddy) : error}
        </p>
      ) : !t ? (
        <div className="flex justify-center p-12"><DotLoader /></div>
      ) : (
        <article className="rounded-2xl border-2 border-b-4 border-line bg-card p-6">
          {/* the cat and what it says */}
          <div className="mb-5 flex items-center gap-4">
            <div className="size-20 shrink-0 overflow-hidden rounded-full border-4 border-sun bg-paper-sunken">
              {t.cat_picture && <img src={t.cat_picture} alt="" className="size-full object-cover" />}
            </div>
            <p aria-live="polite" className={`m-0 rounded-2xl bg-sun-soft px-4 py-3 ${font} text-child-label font-semibold`}>
              {done ? tx.done : say || tx.hello}
            </p>
          </div>

          <div className={`${font} story-spacing mb-5 text-story-md`}>
            {t.display.map((line, i) => (
              <p key={i} className="m-0">
                {line.map((w, j) => {
                  const idx = w.indices.length === 1 ? w.indices[0] : null
                  const caught = idx != null && found.includes(idx)
                  return (
                    <Fragment key={j}>
                      {j > 0 && ' '}
                      <WordToken
                        text={w.text}
                        lang={lang}
                        outcome={caught ? 'self_corrected' : idx != null && shown.includes(idx) ? 'substituted' : 'pending'}
                        onTap={idx != null && !done ? () => tap(idx) : undefined}
                      />
                    </Fragment>
                  )
                })}
              </p>
            ))}
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3">
            <button type="button" onClick={() => play(api.teachAudioUrl(t.id))} disabled={playing}
              className="flex min-h-16 items-center gap-2 rounded-xl border-2 border-b-4 border-sky-edge bg-sky-soft px-5 text-child-label font-bold text-ink active:translate-y-1 disabled:opacity-60">
              <Volume2 size={28} /> <span className={font}>{tx.read(buddy)}</span>
            </button>
            <span className={`${font} font-mono text-child-label tabular-nums text-ink-2`}>{tx.found(found.length, t.mistakes)}</span>
          </div>

          {!done && misses >= 2 && shown.length === 0 && (
            <button type="button" onClick={() => setShown([-1])}
              className="mt-4 flex min-h-14 items-center gap-2 rounded-xl border-2 border-line-strong bg-card px-4 text-child-label text-ink-2">
              <Eye size={24} /> <span className={font}>{tx.showMe}</span>
            </button>
          )}
          {shown.length > 0 && !done && (
            <p className={`mt-4 ${font} text-body text-ink-2`}>
              {lang === 'ne' ? `${buddy}ले फरक पढेका शब्द:` : `The ${buddy} read these differently:`}{' '}
              <ShowMe id={t.id} lang={lang} onShow={setShown} />
            </p>
          )}

          {done && (
            <div className="mt-5 flex justify-end">
              <button type="button" onClick={load}
                className="flex min-h-16 items-center gap-2 rounded-xl border-2 border-b-4 border-primary-hover bg-primary px-6 text-child-label font-bold text-on-primary active:translate-y-1">
                <span className={font}>{tx.again}</span> <ArrowRight size={28} />
              </button>
            </div>
          )}
        </article>
      )}
    </main>
  )
}

// "Show me": the child still taps each word to hear it said properly, so the round ends the
// same way as when they find them alone. The remaining words are marked in the story.
function ShowMe({ id, lang, onShow }: { id: string; lang: Language; onShow: (idx: number[]) => void }) {
  useEffect(() => {
    api.teachHints(id).then((r) => onShow(r.left)).catch(() => {})
  }, [id, onShow])
  return <span className="text-ink-3">{lang === 'ne' ? 'माथि हेर, अनि थिच।' : 'look above, then tap them.'}</span>
}
