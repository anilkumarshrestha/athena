import { Lock } from 'lucide-react'
import { useState, type ReactNode } from 'react'

// Grown-up question (like Duolingo ABC's parent gate): four numbers spelled out in English
// capitals ("ONE, THREE, FOUR, FOUR"), typed as digits (1344). A child learning to read can
// not do it yet; a grown-up can in seconds. Before the parent view, teacher view, story review.
// Child-proofing, not security: the server's family check keeps families apart
// (athena/family.py). Remembered for 10 minutes in this tab.

const KEY = 'athena.grownup'
const TTL_MS = 10 * 60 * 1000

export function grownUpOk(): boolean {
  try {
    return Date.now() - Number(sessionStorage.getItem(KEY) ?? 0) < TTL_MS
  } catch {
    return false
  }
}

function remember() {
  try {
    sessionStorage.setItem(KEY, String(Date.now()))
  } catch {
    /* private mode: ask again next time */
  }
}

const WORDS = ['ZERO', 'ONE', 'TWO', 'THREE', 'FOUR', 'FIVE', 'SIX', 'SEVEN', 'EIGHT', 'NINE']
const newCode = () => Array.from({ length: 4 }, () => Math.floor(Math.random() * 10))

export function ParentGate({ children, onBack }: { children: ReactNode; onBack: () => void }) {
  const [ok, setOk] = useState(grownUpOk)
  const [code, setCode] = useState(newCode)
  const [value, setValue] = useState('')
  const [miss, setMiss] = useState(false)

  if (ok) return <>{children}</>

  const check = () => {
    if (value === code.join('')) {
      remember()
      setOk(true)
    } else {
      setMiss(true)
      setValue('')
      setCode(newCode()) // new numbers, no hint
    }
  }

  return (
    <main className="mx-auto box-content max-w-story px-4 py-12 font-ui md:px-8">
      <section className="flex flex-col items-center gap-4 rounded-2xl border-2 border-b-4 border-line bg-card p-8 text-center">
        <Lock size={40} className="text-ink-2" />
        <h1 className="m-0 text-h2 font-semibold">ठूला मान्छेका लागि · For grown-ups</h1>
        <p className="m-0 text-body text-ink-2">To continue, type these numbers as digits:</p>
        <p className="m-0 text-h2 font-bold tracking-wide">{code.map((d) => WORDS[d]).join(', ')}</p>
        <form onSubmit={(e) => (e.preventDefault(), check())} className="flex gap-2">
          <input value={value} onChange={(e) => setValue(e.target.value.replace(/\D/g, '').slice(0, 4))} inputMode="numeric"
            aria-label="The four numbers as digits" autoFocus placeholder="····"
            className="min-h-14 w-36 rounded-lg border-2 border-line-strong bg-card px-3 text-center font-mono text-stat focus-visible:border-primary" />
          <button type="submit" className="min-h-14 rounded-lg border-b-4 border-primary-hover bg-primary px-5 text-body font-bold text-on-primary">OK</button>
        </form>
        {miss && <p className="m-0 text-small text-ink-3">Not quite. Here are new numbers.</p>}
        <button type="button" onClick={onBack} className="text-body text-ink-3 underline underline-offset-4">Back</button>
      </section>
    </main>
  )
}
