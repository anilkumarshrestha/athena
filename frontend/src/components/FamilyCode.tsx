import { KeyRound, LogOut, UserRound } from 'lucide-react'
import { useEffect, useState } from 'react'
import type { components } from '../api-types'
import { api } from '../api'
import { GoogleButton } from './GoogleButton'
import { bi } from '../ui'

type Family = components['schemas']['FamilyOut']

// Account + family code (athena/family.py), behind the grown-up question. Signing in with
// Google keeps progress on any device; the family code does the same without an account.
export function FamilyCode() {
  const [f, setF] = useState<Family | null>(null)

  useEffect(() => {
    api.family().then(setF).catch(() => {})
  }, [])


  if (!f) return null
  return (
    <section className="mb-8 grid gap-3 md:grid-cols-2">
      <div className="rounded-xl border-2 border-line bg-card p-4">
        <h2 className="m-0 mb-1 flex items-center gap-2 text-h2 font-semibold"><UserRound size={20} /> {bi("खाता", "Account")}</h2>
        {f.email ? (
          <>
            <p className="m-0 mb-2 text-body">Signed in as <span className="font-semibold">{f.email}</span>. Progress is kept with this Google account.</p>
            <button type="button" onClick={() => api.signOut().then(() => location.assign('/app'))}
              className="flex min-h-10 items-center gap-2 rounded-md border border-line-strong px-3 text-body text-ink-2 hover:bg-paper-sunken">
              <LogOut size={18} /> Sign out on this device
            </button>
          </>
        ) : f.google_client_id ? (
          <>
            <p className="m-0 mb-3 text-body">Sign in with Google to keep these children's progress and open it on any device.</p>
            <GoogleButton clientId={f.google_client_id} onSignedIn={() => location.reload()} />
            <p className="m-0 mt-2 text-small text-ink-3">We keep only your Google account id and email, to find your family again.</p>
          </>
        ) : (
          <p className="m-0 text-small text-ink-3">Google sign-in is not set up on this server. The family code works instead.</p>
        )}
      </div>
      <div className="rounded-xl border-2 border-line bg-card p-4">
        <h2 className="m-0 mb-1 flex items-center gap-2 text-h2 font-semibold"><KeyRound size={20} /> {bi("परिवार कोड", "Family code")}</h2>
        <p className="m-0 mb-2 font-mono text-stat tabular-nums">{f.code}</p>
        <p className="m-0 text-small text-ink-3">
          Opens these children on another phone or computer ("Have a family code?" on the first screen). Keep it private, like a password.
        </p>
      </div>
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
        {bi("परिवार कोड छ?", "Have a family code?")}
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
