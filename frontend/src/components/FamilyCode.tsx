import { KeyRound } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api } from '../api'

// Family code (athena/family.py): opens the same children on another device. A secret like a
// password, so it is shown only behind the grown-up question.
export function FamilyCode() {
  const [code, setCode] = useState<string | null>(null)
  useEffect(() => {
    api.family().then((f) => setCode(f.code)).catch(() => {})
  }, [])
  if (!code) return null
  return (
    <section className="mb-8 rounded-xl border-2 border-line bg-card p-4">
      <h2 className="m-0 mb-1 flex items-center gap-2 text-h2 font-semibold"><KeyRound size={20} /> परिवार कोड · Family code</h2>
      <p className="m-0 mb-2 font-mono text-stat tabular-nums">{code}</p>
      <p className="m-0 text-small text-ink-3">
        Opens these children on another phone or computer ("Have a family code?" on the first screen). Keep it private, like a password.
      </p>
    </section>
  )
}

// On the learner screen: open a family from another device with its code.
export function JoinFamily() {
  const [open, setOpen] = useState(false)
  const [code, setCode] = useState('')
  const [error, setError] = useState<string | null>(null)
  if (!open)
    return (
      <button type="button" onClick={() => setOpen(true)} className="text-body text-ink-3 underline underline-offset-4 hover:text-ink-2">
        परिवार कोड छ? · Have a family code?
      </button>
    )
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        setError(null)
        api.joinFamily(code).then(() => location.reload()).catch(() => setError('No family with this code.'))
      }}
      className="flex flex-wrap items-center gap-2"
    >
      <input value={code} onChange={(e) => setCode(e.target.value)} placeholder="a1b2-c3d4-e5f6-a7b8" aria-label="Family code"
        className="min-h-12 rounded-lg border-2 border-line-strong bg-card px-3 font-mono text-body focus-visible:border-primary" />
      <button type="submit" className="min-h-12 rounded-lg border-b-4 border-primary-hover bg-primary px-4 text-body font-bold text-on-primary">Open</button>
      {error && <span className="text-small text-omitted">{error}</span>}
    </form>
  )
}
