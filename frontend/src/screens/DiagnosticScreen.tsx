import { ArrowRight, Check, Volume2 } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import type { components } from '../api-types'
import { api, type Language } from '../api'
import { DotLoader } from '../components/DotLoader'
import { RiverCrossing } from '../components/RiverCrossing'
import { UnitChip } from '../components/UnitChip'

type Diagnostic = components['schemas']['DiagnosticOut']
type Placement = components['schemas']['PlacementOut']

// Placement as a little game: the child's favourite animal crosses a river, one stone per
// round. Round 0: hear a letter, tap it (the child plays alone). Then cards the child reads
// aloud while the adult taps. Never "wrong": every answer just brings the next card.
// Shorter: a round ends after 2 misses, or early after 3 quick correct answers.
// Tier logic mirrors athena/diagnostic.py; the server re-scores every answer.

const chunky =
  'flex min-h-20 flex-1 items-center justify-center gap-3 rounded-xl border-2 border-b-4 px-6 text-child-label font-bold transition-colors duration-150 active:translate-y-1 active:border-b-2'

const QUICK_MS = 4000
const EARLY_PASS = 3
const MISSES_END = 2

// favourite animal id -> Nepali noun (its picture is cached and shared)
const GUIDE: Record<string, { ne: string; en: string }> = {
  goat: { ne: 'खसी', en: 'goat' },
  cat: { ne: 'बिरालो', en: 'cat' },
  dog: { ne: 'कुकुर', en: 'dog' },
  hen: { ne: 'कुखुरा', en: 'hen' },
  cow: { ne: 'गाई', en: 'cow' },
  buffalo: { ne: 'भैंसी', en: 'buffalo' },
  bird: { ne: 'चरा', en: 'bird' },
  yak: { ne: 'याक', en: 'yak' },
}

export function DiagnosticScreen({ learnerId, lang, onDone }: { learnerId: string; lang: Language; onDone: () => void }) {
  const [deck, setDeck] = useState<Diagnostic | null>(null)
  const [guide, setGuide] = useState(GUIDE.goat)
  const [tierIdx, setTierIdx] = useState(0)
  const [cardIdx, setCardIdx] = useState(0)
  const [answers, setAnswers] = useState<Record<string, boolean>>({})
  const [tapped, setTapped] = useState<string | null>(null)
  const [result, setResult] = useState<Placement | null>(null)
  const [error, setError] = useState<string | null>(null)
  const shownAt = useRef(performance.now())
  const run = useRef({ quick: 0, misses: 0 })

  useEffect(() => {
    api.diagnostic(learnerId, lang).then(setDeck).catch((e) => setError(String(e.message ?? e)))
    api.learner(learnerId).then((l) => setGuide(GUIDE[l.profile.favorite_animal ?? ''] ?? GUIDE.goat)).catch(() => {})
  }, [learnerId, lang])

  const tier = deck?.tiers[tierIdx]
  const card = tier?.cards[cardIdx]
  const isNe = lang === 'ne'
  const story = isNe ? 'font-story-ne' : 'font-story-en'

  const say = useCallback((text: string) => {
    new Audio(api.diagnosticSoundUrl(lang, text)).play().catch(() => {})
  }, [lang])

  // Listen cards speak themselves when they appear.
  useEffect(() => {
    shownAt.current = performance.now()
    setTapped(null)
    if (tier?.kind === 'listen' && card) say(card.text)
  }, [tier?.kind, card, say])

  const answer = (ok: boolean) => {
    if (!deck || !tier || !card) return
    const all = { ...answers, [card.id]: ok }
    setAnswers(all)
    const quick = ok && performance.now() - shownAt.current < QUICK_MS
    run.current = { quick: quick ? run.current.quick + 1 : 0, misses: run.current.misses + (ok ? 0 : 1) }

    const isListen = tier.kind === 'listen'
    const lastCard = cardIdx + 1 >= tier.cards.length
    const earlyPass = !isListen && run.current.quick >= EARLY_PASS
    const earlyFail = !isListen && run.current.misses >= MISSES_END
    if (!lastCard && !earlyPass && !earlyFail) return setCardIdx(cardIdx + 1)

    // Round over: listening always leads on to reading; a reading round continues if it went well.
    const asked = tier.cards.filter((c) => c.id in all).map((c) => all[c.id])
    const passed = isListen || earlyPass || (!earlyFail && asked.filter(Boolean).length / asked.length >= deck.pass_rate)
    const next = deck.tiers.findIndex((t, i) => i > tierIdx && (passed || t.always) && !(t.kind === 'listen'))
    run.current = { quick: 0, misses: 0 }
    if (next === -1) {
      api.placement(learnerId, lang, all).then(setResult).catch((e) => setError(String(e.message ?? e)))
      setTierIdx(deck.tiers.length) // no card shown while placing
      return
    }
    setTierIdx(next)
    setCardIdx(0)
  }

  const tapTile = (option: string) => {
    if (!card || tapped) return
    setTapped(option)
    // Same calm transition either way: no "wrong" sound or colour for the child.
    setTimeout(() => answer(option === card.text), 450)
  }

  const stones = deck ? deck.tiers.filter((t) => t.kind === 'read' && !t.always).length + 1 : 0
  const stone = Math.min(stones - 1, deck ? deck.tiers.slice(0, tierIdx).filter((t) => !t.always || t.kind === 'listen').length : 0)
  const pictureUrl = `/api/pictures/ne/${encodeURIComponent(guide.ne)}`

  return (
    <main className="mx-auto box-content flex max-w-story flex-col px-4 py-8 md:px-8">
      <header className="mb-4 flex items-center justify-between gap-4">
        <span className="rounded-full bg-paper-sunken px-3 py-1 text-caption text-ink-2">{isNe ? 'नेपाली' : 'English'}</span>
        <button type="button" onClick={onDone} className="text-body text-ink-3 underline underline-offset-4 hover:text-ink-2">
          Skip
        </button>
      </header>

      {!result && deck && (
        <>
          <p className={`m-0 mb-3 ${story} text-child-label font-semibold`}>
            {isNe ? `${guide.ne}लाई खोला तार्न मद्दत गर!` : `Help the ${guide.en} cross the river!`}
          </p>
          <RiverCrossing stones={stones} current={stone} pictureUrl={pictureUrl} label={`Round ${stone + 1} of ${stones}`} />
        </>
      )}

      {error && <p className="text-body text-omitted">{error}</p>}
      {!deck && !error && <DotLoader />}

      {deck && !result && card && tier?.kind === 'listen' && (
        <>
          <p className="m-0 mb-4 text-body text-ink-3">
            {isNe ? 'सुन, अनि त्यही अक्षर छान।' : 'Listen, then tap that letter.'} (for the child to play alone)
          </p>
          <div className="mb-6 flex justify-center">
            <button type="button" onClick={() => say(card.text)} aria-label="Hear it again"
              className="flex size-24 items-center justify-center rounded-full border-2 border-b-4 border-primary-hover bg-primary text-on-primary active:translate-y-1">
              <Volume2 size={44} strokeWidth={2} />
            </button>
          </div>
          <div className="grid grid-cols-3 gap-4">
            {card.options.map((o) => (
              <button key={`${card.id}-${o}`} type="button" onClick={() => tapTile(o)} disabled={tapped !== null}
                className={`flex min-h-32 items-center justify-center rounded-2xl border-2 border-b-4 ${story} text-[64px] leading-none font-semibold transition-colors duration-150 active:translate-y-1 ${
                  tapped === o ? 'border-primary bg-primary-soft' : 'border-line bg-card hover:bg-paper-sunken'
                }`}>
                {o}
              </button>
            ))}
          </div>
        </>
      )}

      {deck && !result && card && tier?.kind !== 'listen' && (
        <>
          <p className="m-0 mb-4 text-body text-ink-3">
            {isNe ? 'बच्चालाई यो पढ्न भन्नुहोस्।' : 'Ask the child to read this aloud.'} ({tier!.name})
          </p>
          <div className="mb-8 flex min-h-72 items-center justify-center rounded-2xl border-2 border-b-4 border-line bg-card px-6 py-12">
            <span key={card.id} className={`${story} text-[96px] leading-none font-semibold`}>{card.text}</span>
          </div>
          <div className="flex gap-4">
            <button type="button" onClick={() => answer(false)} className={`${chunky} border-line-strong bg-card text-ink-2 hover:bg-paper-sunken`}>
              {isNe ? 'अझै होइन' : 'Not yet'}
            </button>
            <button type="button" onClick={() => answer(true)} className={`${chunky} border-primary-hover bg-primary text-on-primary hover:bg-primary-hover`}>
              <Check size={28} strokeWidth={2.5} />
              {isNe ? 'पढ्यो' : 'Read it'}
            </button>
          </div>
        </>
      )}

      {deck && !result && !card && <DotLoader label="Placing" />}

      {result && (
        <section className="flex flex-1 flex-col items-start gap-6">
          <RiverCrossing stones={stones} current={stones - 1} done pictureUrl={pictureUrl} label="Crossed the river" />
          <h1 className={`m-0 ${story} text-child-title font-bold`}>
            {isNe ? `${guide.ne} पारि पुग्यो! राम्रो!` : `The ${guide.en} crossed the river! Well done!`}
          </h1>
          <p className="m-0 text-body text-ink-2">
            Starting at level {result.level} with {result.mastered} known units. First to practise:
          </p>
          <div className="flex flex-wrap gap-3">
            {result.practicing.map((u) => (
              <UnitChip key={u} unit={u} state="practicing" size="lg" lang={lang} />
            ))}
          </div>
          <button type="button" onClick={onDone} className={`${chunky} flex-none border-primary-hover bg-primary text-on-primary hover:bg-primary-hover`}>
            {isNe ? 'अगाडि' : 'Continue'}
            <ArrowRight size={28} strokeWidth={2.5} />
          </button>
        </section>
      )}
    </main>
  )
}
