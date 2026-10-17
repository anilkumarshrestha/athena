import { Check, Volume2 } from 'lucide-react'
import { useState } from 'react'
import { api, type CloseResult, type Language } from '../api'
import { unitGlyph } from '../units'

type Card = { unit: string; example: string; practising: boolean }

// Letter mode (fewer than 15 readable words): no story, letter cards instead.
// The child hears the example word and says the letter; the adult marks each card,
// and the results feed the same mastery rule as a story, so the child grows into stories.

const chunky =
  'flex min-h-16 items-center justify-center gap-2 rounded-xl border-2 border-b-4 px-5 text-child-label font-bold transition-colors duration-150 active:translate-y-1 active:border-b-2'

export function LetterPractice({
  learnerId,
  lang,
  cards,
  onClosed,
}: {
  learnerId: string
  lang: Language
  cards: Card[]
  onClosed: (r: CloseResult) => void
}) {
  const [said, setSaid] = useState<Record<string, boolean>>({})
  const [saving, setSaving] = useState(false)
  const isNe = lang === 'ne'
  const story = isNe ? 'font-story-ne' : 'font-story-en'
  const play = (unit: string) => new Audio(api.letterAudioUrl(lang, unit)).play().catch(() => {})

  const done = async () => {
    setSaving(true)
    try {
      const results = Object.fromEntries(cards.map((c) => [c.unit, said[c.unit] ?? false]))
      onClosed(await api.closeLetters(learnerId, lang, results))
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="mx-auto w-full max-w-story rounded-2xl border-2 border-b-4 border-line bg-card p-6">
      <h1 className={`m-0 mb-1 ${story} text-child-title font-bold`}>{isNe ? 'अक्षर अभ्यास' : 'Letter practice'}</h1>
      <p className="m-0 mb-6 text-body text-ink-3">
        {isNe ? 'सुन, अनि अक्षर भन।' : 'Listen, then say the letter.'} · For the adult: tap ✓ when the child says it.
      </p>
      <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-3">
        {cards.map((c) => (
          <div
            key={c.unit}
            className={`flex flex-col items-center gap-2 rounded-2xl border-2 border-b-4 p-4 ${
              c.practising ? 'border-substituted bg-substituted-soft' : 'border-line bg-paper'
            }`}
          >
            <span className={`${story} text-[72px] leading-none font-semibold`}>{unitGlyph(c.unit)}</span>
            <button type="button" onClick={() => play(c.unit)} className="flex min-h-12 items-center gap-2 rounded-lg px-3 text-ink-2 hover:bg-paper-sunken">
              <Volume2 size={22} /> <span className={`${story} text-child-label`}>{c.example}</span>
            </button>
            <button
              type="button"
              aria-pressed={!!said[c.unit]}
              onClick={() => setSaid((s) => ({ ...s, [c.unit]: !s[c.unit] }))}
              className={`flex size-12 items-center justify-center rounded-full border-2 ${
                said[c.unit] ? 'border-correct bg-correct text-on-primary' : 'border-line-strong text-ink-4'
              }`}
              aria-label="Child said it"
            >
              <Check size={24} strokeWidth={3} />
            </button>
          </div>
        ))}
      </div>
      <button type="button" disabled={saving} onClick={done} className={`${chunky} w-full border-primary-hover bg-primary text-on-primary hover:bg-primary-hover disabled:bg-ink-4`}>
        {isNe ? 'सकियो' : 'Done'}
      </button>
    </section>
  )
}
