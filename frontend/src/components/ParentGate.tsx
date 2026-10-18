import { Lock } from 'lucide-react'
import { useState, type ReactNode } from 'react'

// Grown-up question (like Duolingo ABC's parent gate): a multiplication a 5-8 year old cannot
// do yet, before the parent view, the teacher view, delete and sign-in. Child-proofing, not
// security: the server's family check is what keeps families apart (athena/family.py).
// Remembered for 10 minutes in this tab.

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

const rand = (lo: number, hi: number) => lo + Math.floor(Math.random() * (hi - lo + 1))

export function ParentGate({ children, onBack }: { children: ReactNode; onBack: () => void }) {
  const [ok, setOk] = useState(grownUpOk)
  const [[a, b], setQ] = useState(() => [rand(6, 9), rand(6, 9)])
  const [value, setValue] = useState('')
  const [miss, setMiss] = useState(false)

  if (ok) return <>{children}</>

  const check = () => {
    if (Number(value) === a * b) {
      remember()
      setOk(true)
    } else {
      setMiss(true)
      setValue('')
      setQ([rand(6, 9), rand(6, 9)]) // a new question, no hint
    }
  }

  return (
    <main className="mx-auto box-content max-w-story px-4 py-12 font-ui md:px-8">
      <section className="flex flex-col items-center gap-4 rounded-2xl border-2 border-b-4 border-line bg-card p-8 text-center">
        <Lock size={40} className="text-ink-2" />
        <h1 className="m-0 text-h2 font-semibold">ठूला मान्छेका लागि · For grown-ups</h1>
        <p className="m-0 text-body text-ink-2">To continue, answer this:</p>
        <p className="m-0 font-mono text-stat tabular-nums">{a} × {b} = ?</p>
        <form onSubmit={(e) => (e.preventDefault(), check())} className="flex gap-2">
          <input value={value} onChange={(e) => setValue(e.target.value.replace(/\D/g, '').slice(0, 3))} inputMode="numeric"
            aria-label="Answer" autoFocus
            className="min-h-14 w-28 rounded-lg border-2 border-line-strong bg-card px-3 text-center font-mono text-stat focus-visible:border-primary" />
          <button type="submit" className="min-h-14 rounded-lg border-b-4 border-primary-hover bg-primary px-5 text-body font-bold text-on-primary">OK</button>
        </form>
        {miss && <p className="m-0 text-small text-ink-3">Not quite. Here is another one.</p>}
        <button type="button" onClick={onBack} className="text-body text-ink-3 underline underline-offset-4">Back</button>
      </section>
    </main>
  )
}
