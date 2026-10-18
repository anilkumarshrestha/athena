import { ArrowLeft, ArrowRight, Check, Moon, Sparkles, Volume2, X } from 'lucide-react'
import { Fragment, useCallback, useEffect, useState } from 'react'
import type { components } from '../api-types'
import { api, type Language } from '../api'
import { DotLoader } from '../components/DotLoader'
import { WordToken } from '../components/WordToken'
import { sfx } from '../sound'

type Maths = components['schemas']['MathsOut']

// A maths word problem the child can read. The numbers and the answer come from code;
// the words were checked readable. Pictures to count; big number tiles; never "wrong":
// a miss dims that tile quietly and offers to count together.

const NE = '०१२३४५६७८९'
const num = (n: number, lang: Language) => (lang === 'ne' ? String(n).replace(/\d/g, (d) => NE[+d]) : String(n))

export function MathsScreen({ learnerId, lang, onBack }: { learnerId: string; lang: Language; onBack: () => void }) {
  const [m, setM] = useState<Maths | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [tried, setTried] = useState<number[]>([])
  const [solved, setSolved] = useState<number | null>(null)
  const [counting, setCounting] = useState(0) // pictures counted so far in "count together"
  const [levelUp, setLevelUp] = useState(false) // bigger numbers from the next problem
  // Teach the cat: on some problems the cat answers first and the child checks it.
  const [catSays, setCatSays] = useState<string | null>(null) // null: still asking the child
  const isNe = lang === 'ne'
  const font = isNe ? 'font-story-ne' : 'font-story-en'

  const load = useCallback(() => {
    setM(null)
    setTried([])
    setSolved(null)
    setCounting(0)
    setError(null)
    setCatSays(null)
    api.mathsStart(learnerId, lang).then(setM).catch((e) => setError(String(e.message ?? e)))
  }, [learnerId, lang])
  useEffect(load, [load])

  const countTogether = (total: number) => {
    setCounting(0)
    for (let i = 1; i <= total; i++) setTimeout(() => (setCounting(i), sfx.pop()), i * 550)
  }

  const answer = async (n: number) => {
    if (!m || solved !== null || tried.includes(n)) return
    const r = await api.mathsAnswer(m.id, n)
    setLevelUp(r.level_change === 'up') // a step down is never announced to the child
    if (r.correct) {
      setSolved(n)
      sfx.chime()
    } else {
      setTried((t) => [...t, n]) // silent: no "wrong" sound
      if (r.answer != null) countTogether(m.op === '+' ? m.a + m.b : m.a)
    }
  }

  const judge = async (saysRight: boolean) => {
    if (!m) return
    const r = await api.mathsJudge(m.id, saysRight)
    const total = m.op === '+' ? m.a + m.b : m.a
    if (r.cat_was_right && saysRight) {
      setCatSays(isNe ? 'हो! मैले ठीक भनेँ। धन्यवाद!' : 'Yes! I was right. Thank you!')
      setSolved(m.cat_answer!)
      setLevelUp(r.result?.level_change === 'up')
      sfx.chime()
    } else if (!r.cat_was_right && !saysRight) {
      setCatSays(isNe ? 'हो, मैले गल्ती गरेँ! अब तिमी देखाऊ।' : 'Oh, I made a mistake! Now you show me.')
      sfx.pop()
    } else {
      setCatSays(isNe ? 'सँगै गनेर हेरौँ।' : "Let's count together and see.")
      countTogether(total) // checking together, never "wrong"
    }
  }
  const asking = m?.cat_answer != null && catSays === null

  // a pictures, then (+) b more, or (−) the last b crossed out
  const pictures = m ? (m.op === '+' ? m.a + m.b : m.a) : 0
  const takenFrom = m && m.op === '-' ? m.a - m.b : Infinity

  return (
    <main className="mx-auto box-content max-w-story px-4 pb-16 pt-4 md:px-8">
      <button type="button" onClick={onBack} aria-label="Back" className="mb-4 flex size-16 items-center justify-center rounded-full text-ink-2 hover:bg-paper-sunken">
        <ArrowLeft size={32} strokeWidth={1.75} />
      </button>
      {error === 'daily_limit' ? (
        <section className="flex flex-col items-center gap-4 rounded-2xl border-2 border-b-4 border-line bg-card p-12 text-center">
          <Moon size={64} strokeWidth={1.5} className="text-primary" />
          <p className="m-0 font-story-ne text-child-title font-bold">आजलाई यति नै! भोलि फेरि खेलौँ।</p>
          <p className="m-0 font-story-en text-child-label text-ink-2">That's all for today. Let's play again tomorrow!</p>
        </section>
      ) : error ? <p className="text-omitted">{error}</p> : null}
      {!m && !error && <div className="flex justify-center p-12"><DotLoader label="Making a problem" /></div>}

      {m && (
        <article className="rounded-2xl border-2 border-b-4 border-line bg-card p-6">
          <div className="mb-4 flex items-start justify-between gap-3">
            <div className={`${font} story-spacing text-story-md`}>
              {m.display.map((line, i) => (
                <p key={i} className="m-0">
                  {line.map((w, j) => (
                    <Fragment key={j}>
                      {j > 0 && ' '}
                      <WordToken text={w.text} lang={lang} />
                    </Fragment>
                  ))}
                </p>
              ))}
            </div>
            <button type="button" aria-label="Read it to me" onClick={() => new Audio(api.mathsAudioUrl(m.id)).play().catch(() => {})}
              className="flex size-16 shrink-0 items-center justify-center rounded-xl border-2 border-b-4 border-sky-edge bg-sky-soft text-ink active:translate-y-1">
              <Volume2 size={28} />
            </button>
          </div>

          {m.picture_url && (
            <div className="mb-6 flex flex-wrap items-center gap-2 rounded-xl bg-paper-sunken p-3" aria-label={`${m.a} ${m.op} ${m.b}`}>
              {Array.from({ length: pictures }, (_, i) => {
                const gone = i >= takenFrom
                const gap = m.op === '+' && i === m.a
                return (
                  <Fragment key={i}>
                    {gap && <span className="px-1 font-mono text-stat text-ink-3">+</span>}
                    <span className={`relative inline-block size-14 ${gone ? 'opacity-40' : ''}`}>
                      <img src={m.picture_url!} alt="" className={`size-14 rounded-lg object-cover ${counting > i ? 'ring-4 ring-sun' : ''}`} />
                      {gone && <span aria-hidden className="absolute left-0 top-1/2 h-1 w-full -rotate-45 rounded bg-ink-2" />}
                      {counting > i && (
                        <span className="absolute -right-1 -top-1 flex size-6 items-center justify-center rounded-full bg-sun font-mono text-caption font-bold text-on-sun">
                          {num(i + 1, lang)}
                        </span>
                      )}
                    </span>
                  </Fragment>
                )
              })}
            </div>
          )}

          {m.cat_answer != null && (
            <div className="mb-5 flex items-center gap-4">
              <div className="size-16 shrink-0 overflow-hidden rounded-full border-4 border-sun bg-paper-sunken">
                <img src="/api/pictures/ne/बिरालो" alt="" className="size-full object-cover" />
              </div>
              <div className={`rounded-2xl bg-sun-soft px-4 py-3 ${font} text-child-label font-semibold`}>
                {catSays ?? (
                  <>
                    {isNe ? 'मेरो उत्तर' : 'My answer'}: <span className="font-mono text-stat">{num(m.cat_answer, lang)}</span>.{' '}
                    {isNe ? 'ठीक हो?' : 'Am I right?'}
                  </>
                )}
              </div>
            </div>
          )}
          {asking && (
            <div className="grid grid-cols-2 gap-3">
              <button type="button" onClick={() => judge(true)}
                className={`flex min-h-20 items-center justify-center gap-2 rounded-2xl border-2 border-b-4 border-line bg-card ${font} text-child-label font-bold active:translate-y-1`}>
                <Check size={32} /> {isNe ? 'ठीक छ' : 'Right'}
              </button>
              <button type="button" onClick={() => judge(false)}
                className={`flex min-h-20 items-center justify-center gap-2 rounded-2xl border-2 border-b-4 border-line bg-card ${font} text-child-label font-bold active:translate-y-1`}>
                <X size={32} /> {isNe ? 'ठीक छैन' : 'Not right'}
              </button>
            </div>
          )}

          <div className={`grid grid-cols-4 gap-3 ${asking ? 'hidden' : ''}`}>
            {m.choices.map((n) => {
              const right = solved === n
              const missed = tried.includes(n)
              return (
                <button key={n} type="button" disabled={missed || solved !== null} onClick={() => answer(n)}
                  className={`flex min-h-20 items-center justify-center rounded-2xl border-2 border-b-4 font-mono text-[44px] font-bold transition-colors duration-150 active:translate-y-1 ${
                    right ? 'border-leaf-edge bg-leaf text-on-primary' : missed ? 'border-line bg-paper-sunken text-ink-4' : 'border-line bg-card text-ink hover:bg-paper-sunken'
                  }`}>
                  {num(n, lang)}
                  {right && <span className="ml-1 text-[28px]">✓</span>}
                </button>
              )
            })}
          </div>

          <div aria-live="polite" className={`mt-5 min-h-10 text-center ${font} text-child-label font-semibold`}>
            {solved !== null && <span className="text-correct">{isNe ? 'धेरै राम्रो!' : 'Well done!'}</span>}
            {solved !== null && levelUp && (
              <span className="mt-2 flex items-center justify-center gap-2 text-ink">
                <Sparkles size={24} className="text-sun" /> {isNe ? 'अब ठूला अङ्क!' : 'Bigger numbers next!'}
              </span>
            )}
            {solved === null && tried.length > 0 && (
              <button type="button" onClick={() => countTogether(pictures)} className="text-ink-2 underline underline-offset-4">
                {isNe ? 'सँगै गनौँ!' : "Let's count together!"}
              </button>
            )}
          </div>

          {solved !== null && (
            <div className="mt-2 flex justify-end">
              <button type="button" onClick={load} className="flex min-h-16 items-center gap-2 rounded-xl border-2 border-b-4 border-primary-hover bg-primary px-6 text-child-label font-bold text-on-primary active:translate-y-1">
                {isNe ? 'अर्को' : 'Next'} <ArrowRight size={28} />
              </button>
            </div>
          )}
        </article>
      )}
    </main>
  )
}
