import { ArrowRight, BookOpenCheck, HeartHandshake, Mic, ShieldCheck, Sparkles, UserRound } from 'lucide-react'
import { useCallback, useState } from 'react'
import type { components } from '../api-types'
import { api } from '../api'
import { DotLoader } from '../components/DotLoader'
import { GoogleButton } from '../components/GoogleButton'
import { go } from '../nav'

type Family = components['schemas']['FamilyOut']

// Landing page for grown-ups: what Athena is, then Start:
//   1. sign in with Google, or continue without an account (a private family on this browser)
//   2. add your child (onboarding), or skip and try the demo children
// A returning family goes straight to its children.

const pic = (noun: string) => `/api/pictures/ne/${noun}`

const FEATURES = [
  { icon: Sparkles, ne: 'आफ्नै कथा', en: 'Stories written for one child', text: "About their favourite animal, food and games. Every word uses only letters they can read, checked by code, not by the AI." },
  { icon: Mic, ne: 'सँगै पढ्छ', en: 'Listens as they read aloud', text: 'Follows each word, notices where they get stuck, and helps in the way that works for them. Never says "wrong".' },
  { icon: BookOpenCheck, ne: 'अक्षरदेखि कथासम्म', en: 'Letters, stories and maths', text: 'A playful card check finds the starting point; new letters come when they unlock the most words.' },
  { icon: HeartHandshake, ne: 'अभिभावकका लागि', en: 'Clear for parents', text: 'What they learned this week, what is hard, why each story was chosen, ideas for home, time limits.' },
]

export function Landing() {
  const [step, setStep] = useState<'hero' | 'account' | 'learner'>('hero')
  const [family, setFamily] = useState<Family | null>(null)
  const [busy, setBusy] = useState(false)

  const start = async () => {
    setBusy(true)
    try {
      const f = await api.family()
      setFamily(f)
      if (f.email) go('/app') // returning family: straight to the children
      else setStep('account')
    } catch {
      setStep('account')
    } finally {
      setBusy(false)
    }
  }
  const signedIn = useCallback(() => {
    api.family().then(setFamily).catch(() => {})
    setStep('learner')
  }, [])

  const card = 'rounded-2xl border-2 border-b-4 border-line bg-card p-6'
  const primary =
    'flex min-h-16 w-full items-center justify-center gap-2 rounded-xl border-b-4 border-primary-hover bg-primary px-6 text-child-label font-bold text-on-primary active:translate-y-1'
  const secondary =
    'flex min-h-16 w-full items-center justify-center gap-2 rounded-xl border-2 border-b-4 border-line-strong bg-card px-6 text-child-label font-semibold text-ink active:translate-y-1'

  if (step === 'account')
    return (
      <main className="mx-auto box-content max-w-story px-4 py-12 font-ui md:px-8">
        <section className={`${card} flex flex-col items-center gap-5 text-center`}>
          <UserRound size={40} className="text-primary" />
          <h1 className="m-0 font-story-ne text-child-title font-bold">खाता · Your account</h1>
          <p className="m-0 max-w-prose text-body text-ink-2">
            Sign in with Google to keep your children's progress and open it on any device. Or continue without an account:
            everything stays private to this browser, and you can sign in later from the parent view.
          </p>
          {family?.google_client_id ? (
            <GoogleButton clientId={family.google_client_id} onSignedIn={signedIn} />
          ) : (
            <p className="m-0 text-small text-ink-3">Google sign-in is not set up on this server.</p>
          )}
          <button type="button" onClick={() => setStep('learner')} className={secondary}>
            खाता बिना अगाडि · Continue without an account <ArrowRight size={24} />
          </button>
          <p className="m-0 flex items-center gap-2 text-small text-ink-3">
            <ShieldCheck size={16} /> We keep only your Google account id and email. Children: first name only, no audio kept.
          </p>
        </section>
      </main>
    )

  if (step === 'learner')
    return (
      <main className="mx-auto box-content max-w-story px-4 py-12 font-ui md:px-8">
        <section className={`${card} flex flex-col items-center gap-5 text-center`}>
          <img src={pic('किताब')} alt="" className="size-24 rounded-2xl object-cover" />
          <h1 className="m-0 font-story-ne text-child-title font-bold">तपाईंको बच्चा · Your child</h1>
          {family?.email && <p className="m-0 text-body text-ink-2">Signed in as <span className="font-semibold">{family.email}</span>.</p>}
          <p className="m-0 max-w-prose text-body text-ink-2">
            Add your child: about a minute together, then a short letter game finds where to start. Or skip and try Athena with
            two demo children first.
          </p>
          <a href="/new" className={primary}>
            बच्चा थप्नुहोस् · Add your child <ArrowRight size={24} />
          </a>
          <a href="/app" className={secondary}>
            पछि · Skip, try the demo children
          </a>
        </section>
      </main>
    )

  return (
    <main className="mx-auto box-content max-w-[1100px] px-4 pb-16 pt-8 font-ui md:px-8">
      <header className="mb-10 flex items-center gap-3">
        <svg viewBox="0 0 32 32" className="size-10" aria-hidden>
          <path d="M8 25 16 6l8 19M11.5 18h9" fill="none" className="stroke-crimson" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <span className="text-child-title font-semibold">Athena</span>
      </header>

      {/* hero */}
      <section className="mb-12 grid items-center gap-8 md:grid-cols-2">
        <div>
          <h1 className="m-0 mb-3 font-story-ne text-display font-bold">आफ्नै कथा, आफ्नै अक्षरमा।</h1>
          <p className="m-0 mb-4 text-h2 font-semibold text-ink-2">A reading friend that writes stories for your child.</p>
          <p className="m-0 mb-6 text-body text-ink-2">
            For children aged 5 to 8 learning to read Nepali and English. Each story uses only the letters your child can read
            today, about the things they love, and grows with them, letter by letter.
          </p>
          <button type="button" onClick={start} disabled={busy} className={`${primary} md:w-auto`}>
            {busy ? <DotLoader /> : <>सुरु गरौँ · Start <ArrowRight size={26} /></>}
          </button>
        </div>
        <div className="grid grid-cols-3 gap-3" aria-hidden>
          {['बिरालो', 'चङ्गा', 'मोमो', 'हिमाल', 'किताब', 'खरायो'].map((n) => (
            <img key={n} src={pic(n)} alt="" className="aspect-square w-full rounded-2xl border-2 border-line bg-sky-soft object-cover"
              onError={(e) => (e.currentTarget.style.visibility = 'hidden')} />
          ))}
        </div>
      </section>

      {/* what it does */}
      <section className="mb-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {FEATURES.map((f) => (
          <article key={f.en} className={card}>
            <f.icon size={32} className="mb-3 text-primary" />
            <h2 className="m-0 font-story-ne text-h3 font-bold">{f.ne}</h2>
            <p className="m-0 mb-2 text-body font-semibold">{f.en}</p>
            <p className="m-0 text-small text-ink-2">{f.text}</p>
          </article>
        ))}
      </section>

      <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-line pt-6 text-small text-ink-3">
        <span className="flex items-center gap-2">
          <ShieldCheck size={16} /> Every story is checked for child safety. First name only, no recordings kept.
        </span>
        <a href="/app" className="underline underline-offset-4">Already here? Go to your children</a>
      </footer>
    </main>
  )
}
