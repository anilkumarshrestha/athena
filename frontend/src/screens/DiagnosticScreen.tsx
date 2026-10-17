import { Check, ArrowRight } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import type { components } from '../api-types'
import { api, type Language } from '../api'
import { DotLoader } from '../components/DotLoader'
import { UnitChip } from '../components/UnitChip'

type Diagnostic = components['schemas']['DiagnosticOut']
type Placement = components['schemas']['PlacementOut']

// Placement card check. The child reads the card aloud; the adult beside them taps.
// The child never sees "wrong": either button just brings the next card.
// Tier logic mirrors athena/diagnostic.py; the server re-scores the answers.

const chunky =
  'flex min-h-20 flex-1 items-center justify-center gap-3 rounded-xl border-2 border-b-4 px-6 text-child-label font-bold transition-colors duration-150 active:translate-y-1 active:border-b-2'

export function DiagnosticScreen({
  learnerId,
  lang,
  onDone,
}: {
  learnerId: string
  lang: Language
  onDone: () => void
}) {
  const [deck, setDeck] = useState<Diagnostic | null>(null)
  const [tierIdx, setTierIdx] = useState(0)
  const [cardIdx, setCardIdx] = useState(0)
  const [answers, setAnswers] = useState<Record<string, boolean>>({})
  const [result, setResult] = useState<Placement | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.diagnostic(learnerId, lang).then(setDeck).catch((e) => setError(String(e.message ?? e)))
  }, [learnerId, lang])

  const tier = deck?.tiers[tierIdx]
  const card = tier?.cards[cardIdx]
  const total = useMemo(() => deck?.tiers.reduce((n, t) => n + t.cards.length, 0) ?? 0, [deck])
  const done = Object.keys(answers).length

  const finish = (all: Record<string, boolean>) => {
    api
      .placement(learnerId, lang, all)
      .then(setResult)
      .catch((e) => setError(String(e.message ?? e)))
  }

  const answer = (read: boolean) => {
    if (!deck || !tier || !card) return
    const all = { ...answers, [card.id]: read }
    setAnswers(all)
    if (cardIdx + 1 < tier.cards.length) return setCardIdx(cardIdx + 1)

    // Tier finished: continue if it was easy enough, else skip to the always-asked tiers.
    const asked = tier.cards.map((c) => all[c.id])
    const passed = asked.filter(Boolean).length / asked.length >= deck.pass_rate
    const next = deck.tiers.findIndex((t, i) => i > tierIdx && (passed || t.always))
    if (next === -1) return finish(all)
    setTierIdx(next)
    setCardIdx(0)
  }

  const isNe = lang === 'ne'
  const story = isNe ? 'font-story-ne' : 'font-story-en'

  return (
    <main className="mx-auto box-content flex max-w-story flex-col px-4 py-8 md:px-8">
      <header className="mb-6 flex items-center justify-between gap-4">
        <span className="rounded-full bg-paper-sunken px-3 py-1 text-caption text-ink-2">{isNe ? 'नेपाली' : 'English'}</span>
        {!result && deck && (
          <span aria-label={`${done} of up to ${total}`} className="flex flex-wrap gap-1.5">
            {Array.from({ length: total }, (_, i) => (
              <span key={i} className={`size-2.5 rounded-full ${i < done ? 'bg-primary' : 'bg-line'}`} />
            ))}
          </span>
        )}
        <button type="button" onClick={onDone} className="text-body text-ink-3 underline underline-offset-4 hover:text-ink-2">
          Skip
        </button>
      </header>

      {error && <p className="text-body text-omitted">{error}</p>}
      {!deck && !error && (
        <div className="flex flex-1 items-center justify-center">
          <DotLoader />
        </div>
      )}

      {deck && !result && card && (
        <>
          <p className="m-0 mb-4 text-body text-ink-3">
            {isNe ? 'बच्चालाई यो पढ्न भन्नुहोस्।' : 'Ask the child to read this aloud.'} ({tier!.name})
          </p>
          <div className="mb-8 flex min-h-72 items-center justify-center rounded-2xl border-2 border-b-4 border-line bg-card px-6 py-12">
            <span key={card.id} className={`${story} text-[96px] leading-none font-semibold`}>
              {card.text}
            </span>
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
          <h1 className={`m-0 ${story} text-child-title font-bold`}>{isNe ? 'राम्रो!' : 'Well done!'}</h1>
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
