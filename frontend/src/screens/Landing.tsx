import { ArrowRight, BookOpenCheck, HeartHandshake, Mic, ShieldCheck, Sparkles, UserRound } from 'lucide-react'
import { useCallback, useState } from 'react'
import type { components } from '../api-types'
import { api } from '../api'
import { DotLoader } from '../components/DotLoader'
import { GoogleButton } from '../components/GoogleButton'
import { go } from '../nav'

type Family = components['schemas']['FamilyOut']
type UiLang = 'en' | 'ne'

// Landing page for grown-ups, in English or Nepali (switch top right, remembered here):
// what Athena is, then Start:
//   1. sign in with Google, or continue without an account (a private family on this browser)
//   2. add your child (onboarding), or skip and try the demo children
// A returning signed-in family goes straight to its children.

const pic = (noun: string) => `/api/pictures/ne/${noun}`
const KEY = 'athena.uiLang'

const T = {
  en: {
    title: 'A reading friend that writes stories for your child.',
    lead: 'For children aged 4 and up learning to read Nepali and English. Each story uses only the letters your child can read today, about the things they love, and grows with them, letter by letter.',
    start: 'Start',
    features: [
      ['Stories written for one child', 'About their favourite animal, food and games. Every word uses only letters they can read, checked by code, not by the AI.'],
      ['Listens as they read aloud', 'Follows each word, notices where they get stuck, and helps in the way that works for them. Never says "wrong".'],
      ['Letters, stories and maths', 'A playful letter game finds the starting point; new letters come when they unlock the most words.'],
      ['Clear for parents', 'What they learned this week, what is hard, why each story was chosen, ideas for home, time limits.'],
    ],
    safety: 'Every story is checked for child safety. First name only, no recordings kept.',
    already: 'Already here? Go to your children',
    accountTitle: 'Your account',
    accountText: "Sign in with Google to keep your children's progress and open it on any device. Or continue without an account: everything stays private to this browser, and you can sign in later from the parent view.",
    noGoogle: 'Google sign-in is not set up on this server.',
    continue: 'Continue without an account',
    keep: 'We keep only your Google account id and email. Children: first name only, no audio kept.',
    childTitle: 'Your child',
    signedAs: 'Signed in as',
    childText: 'Add your child: about a minute together, then a short letter game finds where to start. Or skip and try Athena with two demo children first.',
    add: 'Add learner (child)',
    skip: 'Skip, try demo',
  },
  ne: {
    title: 'तपाईंको बच्चाका लागि कथा लेख्ने पढाइ-साथी।',
    lead: '४ वर्ष र सोभन्दा माथिका, नेपाली र अङ्ग्रेजी पढ्न सिक्दै गरेका बालबालिकाका लागि। हरेक कथामा बच्चाले आज पढ्न सक्ने अक्षर मात्र हुन्छन्, उसलाई मन पर्ने कुराबारे, र अक्षर-अक्षर गर्दै उसैसँग बढ्छ।',
    start: 'सुरु गरौँ',
    features: [
      ['एउटै बच्चाका लागि लेखिएका कथा', 'मन पर्ने जनावर, खाना र खेलबारे। हरेक शब्दमा बच्चाले पढ्न सक्ने अक्षर मात्र, AI ले होइन, कोडले जाँचेको।'],
      ['ठूलो स्वरले पढ्दा सुन्छ', 'हरेक शब्द पछ्याउँछ, कहाँ अड्कियो थाहा पाउँछ, र बच्चालाई मिल्ने तरिकाले मद्दत गर्छ। कहिल्यै "गलत" भन्दैन।'],
      ['अक्षर, कथा र गणित', 'रमाइलो अक्षर-खेलले सुरु गर्ने ठाउँ पत्ता लगाउँछ; धेरै शब्द खोल्ने नयाँ अक्षर पछि आउँछन्।'],
      ['अभिभावकका लागि स्पष्ट', 'यो हप्ता के सिक्यो, के गाह्रो छ, हरेक कथा किन छानियो, घरमा गर्ने अभ्यास, समय सीमा।'],
    ],
    safety: 'हरेक कथा बाल-सुरक्षाका लागि जाँचिन्छ। पहिलो नाम मात्र, कुनै रेकर्डिङ राखिँदैन।',
    already: 'पहिले नै सुरु गर्नुभएको? बच्चाहरूतिर जानुहोस्',
    accountTitle: 'तपाईंको खाता',
    accountText: 'बच्चाको प्रगति राख्न र जुनसुकै उपकरणमा खोल्न Google बाट साइन इन गर्नुहोस्। वा खाता बिना अगाडि बढ्नुहोस्: सबै कुरा यही ब्राउजरमा गोप्य रहन्छ, र पछि अभिभावक पृष्ठबाट साइन इन गर्न सकिन्छ।',
    noGoogle: 'यो सर्भरमा Google साइन इन मिलाइएको छैन।',
    continue: 'खाता बिना अगाडि बढ्नुहोस्',
    keep: 'हामी तपाईंको Google खाता नम्बर र इमेल मात्र राख्छौँ। बच्चाको पहिलो नाम मात्र, कुनै आवाज राखिँदैन।',
    childTitle: 'तपाईंको बच्चा',
    signedAs: 'साइन इन:',
    childText: 'बच्चा थप्नुहोस्: सँगै करिब एक मिनेट, त्यसपछि छोटो अक्षर-खेलले सुरु गर्ने ठाउँ पत्ता लगाउँछ। वा पहिले दुई नमुना बच्चासँग Athena चलाएर हेर्नुहोस्।',
    add: 'बच्चा थप्नुहोस्',
    skip: 'पछि, नमुना हेर्नुहोस्',
  },
} as const

const ICONS = [Sparkles, Mic, BookOpenCheck, HeartHandshake]

function initialLang(): UiLang {
  try {
    return localStorage.getItem(KEY) === 'ne' ? 'ne' : 'en'
  } catch {
    return 'en'
  }
}

export function Landing() {
  const [lang, setLang] = useState<UiLang>(initialLang)
  const [step, setStep] = useState<'hero' | 'account' | 'learner'>('hero')
  const [family, setFamily] = useState<Family | null>(null)
  const [busy, setBusy] = useState(false)
  const t = T[lang]
  const font = lang === 'ne' ? 'font-story-ne' : 'font-ui'

  const choose = (l: UiLang) => {
    setLang(l)
    try {
      localStorage.setItem(KEY, l)
    } catch {
      /* not remembered: fine */
    }
  }

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

  const header = (
    <header className="mb-10 flex items-center gap-3">
      <svg viewBox="0 0 32 32" className="size-10" aria-hidden>
        <path d="M8 25 16 6l8 19M11.5 18h9" fill="none" className="stroke-crimson" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <span className="text-child-title font-semibold">Athena</span>
      <div role="group" aria-label="Language" className="ml-auto flex rounded-lg border border-line-strong bg-card p-1">
        {(['en', 'ne'] as const).map((l) => (
          <button key={l} type="button" aria-pressed={lang === l} onClick={() => choose(l)}
            className={`min-h-10 rounded-md px-3 text-body ${l === 'ne' ? 'font-story-ne' : ''} ${lang === l ? 'bg-primary-soft font-semibold text-primary' : 'text-ink-2 hover:bg-paper-sunken'}`}>
            {l === 'en' ? 'English' : 'नेपाली'}
          </button>
        ))}
      </div>
    </header>
  )

  if (step === 'account')
    return (
      <main className={`mx-auto box-content max-w-story px-4 py-8 ${font} md:px-8`}>
        {header}
        <section className={`${card} flex flex-col items-center gap-5 text-center`}>
          <UserRound size={40} className="text-primary" />
          <h1 className="m-0 text-child-title font-bold">{t.accountTitle}</h1>
          <p className="m-0 max-w-prose text-body text-ink-2">{t.accountText}</p>
          {family?.google_client_id ? (
            <GoogleButton clientId={family.google_client_id} onSignedIn={signedIn} />
          ) : (
            <p className="m-0 text-small text-ink-3">{t.noGoogle}</p>
          )}
          <button type="button" onClick={() => setStep('learner')} className={secondary}>
            {t.continue} <ArrowRight size={24} />
          </button>
          <p className="m-0 flex items-center gap-2 text-small text-ink-3">
            <ShieldCheck size={16} className="shrink-0" /> {t.keep}
          </p>
        </section>
      </main>
    )

  if (step === 'learner')
    return (
      <main className={`mx-auto box-content max-w-story px-4 py-8 ${font} md:px-8`}>
        {header}
        <section className={`${card} flex flex-col items-center gap-5 text-center`}>
          <img src={pic('किताब')} alt="" className="size-24 rounded-2xl object-cover" />
          <h1 className="m-0 text-child-title font-bold">{t.childTitle}</h1>
          {family?.email && (
            <p className="m-0 text-body text-ink-2">
              {t.signedAs} <span className="font-ui font-semibold">{family.email}</span>
            </p>
          )}
          <p className="m-0 max-w-prose text-body text-ink-2">{t.childText}</p>
          <a href="/new" className={primary}>
            {t.add} <ArrowRight size={24} />
          </a>
          <a href="/app" className={secondary}>{t.skip}</a>
        </section>
      </main>
    )

  return (
    <main className={`mx-auto box-content max-w-[1100px] px-4 pb-16 pt-8 ${font} md:px-8`}>
      {header}

      <section className="mb-12 grid items-center gap-8 md:grid-cols-2">
        <div>
          <h1 className="m-0 mb-4 text-display font-bold">{t.title}</h1>
          <p className="m-0 mb-6 text-body text-ink-2">{t.lead}</p>
          <button type="button" onClick={start} disabled={busy} className={`${primary} md:w-auto`}>
            {busy ? <DotLoader /> : <>{t.start} <ArrowRight size={26} /></>}
          </button>
        </div>
        <div className="grid grid-cols-3 gap-3" aria-hidden>
          {['बिरालो', 'चङ्गा', 'मोमो', 'हिमाल', 'किताब', 'खरायो'].map((n) => (
            <img key={n} src={pic(n)} alt="" className="aspect-square w-full rounded-2xl border-2 border-line bg-sky-soft object-cover"
              onError={(e) => (e.currentTarget.style.visibility = 'hidden')} />
          ))}
        </div>
      </section>

      <section className="mb-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {t.features.map(([title, text], i) => {
          const Icon = ICONS[i]
          return (
            <article key={title} className={card}>
              <Icon size={32} className="mb-3 text-primary" />
              <h2 className="m-0 mb-2 text-h3 font-bold">{title}</h2>
              <p className="m-0 text-small text-ink-2">{text}</p>
            </article>
          )
        })}
      </section>

      <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-line pt-6 text-small text-ink-3">
        <span className="flex items-center gap-2">
          <ShieldCheck size={16} className="shrink-0" /> {t.safety}
        </span>
        <a href="/app" className="underline underline-offset-4">{t.already}</a>
      </footer>
    </main>
  )
}
