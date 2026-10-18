import { Check, ShieldCheck } from 'lucide-react'
import { useEffect, useState } from 'react'
import type { components } from '../api-types'
import { api } from '../api'

type Controls = components['schemas']['ControlsIn']
type ThemeOption = components['schemas']['ThemeOptionOut']

// Parent content controls: which activities are offered, story pictures, themes to avoid.
// On/off is shown by a check mark and the word "On"/"Off", never by colour alone (§2).

const SWITCHES: { key: 'maths' | 'teach' | 'pictures'; ne: string; en: string; hint: string }[] = [
  { key: 'maths', ne: 'गणित', en: 'Maths', hint: 'Word problems on the learner card.' },
  { key: 'teach', ne: 'बिरालोलाई सिकाऊ', en: 'Teach the cat', hint: 'Catching the cat\'s reading and maths mistakes.' },
  { key: 'pictures', ne: 'कथाका चित्र', en: 'Story pictures', hint: 'Off: no AI picture is made for stories (maths counting pictures stay).' },
]

const chip = (on: boolean) =>
  `flex min-h-10 items-center gap-2 rounded-md border px-3 text-body ${on ? 'border-primary bg-primary-soft text-primary' : 'border-line-strong text-ink-2 hover:bg-paper-sunken'}`

export function ContentControls({ learnerId, initial }: { learnerId: string; initial: Record<string, unknown> }) {
  const [c, setC] = useState<Controls>({
    maths: initial.maths !== false,
    teach: initial.teach !== false,
    pictures: initial.pictures !== false,
    avoid_themes: (initial.avoid_themes as string[]) ?? [],
  })
  const [themes, setThemes] = useState<ThemeOption[]>([])

  useEffect(() => {
    api.themes().then(setThemes).catch(() => {})
  }, [])

  const save = (next: Controls) => {
    setC(next)
    api.setControls(learnerId, next).catch(() => setC(c)) // undo on failure
  }
  const avoid = c.avoid_themes ?? []

  return (
    <section className="mb-8 rounded-xl border-2 border-line bg-card p-4">
      <h2 className="m-0 mb-1 flex items-center gap-2 text-h2 font-semibold"><ShieldCheck size={20} /> सामग्री · Content</h2>
      <p className="m-0 mb-3 text-small text-ink-3">Every story is already checked for child safety. These choose what is offered.</p>
      <div className="mb-4 grid gap-2 md:grid-cols-3">
        {SWITCHES.map((sw) => {
          const on = c[sw.key] !== false
          return (
            <button key={sw.key} type="button" aria-pressed={on} onClick={() => save({ ...c, [sw.key]: !on })}
              className={`flex flex-col items-start rounded-lg border-2 p-3 text-left ${on ? 'border-primary bg-primary-soft' : 'border-line bg-card'}`}>
              <span className="flex items-center gap-2 font-semibold">
                {on ? <Check size={18} className="text-primary" /> : <span className="inline-block size-[18px] rounded-sm border-2 border-line-strong" />}
                <span className="font-story-ne">{sw.ne}</span> · {sw.en}: {on ? 'On' : 'Off'}
              </span>
              <span className="text-small text-ink-3">{sw.hint}</span>
            </button>
          )
        })}
      </div>
      <h3 className="m-0 mb-2 text-h3 font-semibold">यी विषयमा कथा नबनाऊ · Themes to avoid</h3>
      <div className="flex flex-wrap gap-2">
        {themes.map((t) => {
          const off = avoid.includes(t.theme)
          return (
            <button key={t.theme} type="button" aria-pressed={off}
              onClick={() => save({ ...c, avoid_themes: off ? avoid.filter((x) => x !== t.theme) : [...avoid, t.theme] })}
              className={chip(off)}>
              {off && <Check size={16} />}
              <span className="font-story-ne">{t.label_ne}</span> <span className="text-small">· {t.label_en}</span>
            </button>
          )
        })}
      </div>
      <p className="m-0 mt-2 text-small text-ink-3">Ticked themes are never written or offered. Favourite-animal and food stories stay.</p>
    </section>
  )
}
