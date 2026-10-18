import { Languages } from 'lucide-react'
import { useState } from 'react'
import type { components } from '../api-types'
import { DotLoader } from './DotLoader'

type Gloss = components['schemas']['GlossOut']

// "Show in English" for grown-ups who do not read Devanagari: each Nepali sentence romanised
// (in code) and translated (athena/gloss.py). Never reading material for the child.
export function EnglishGloss({ load }: { load: () => Promise<Gloss> }) {
  const [open, setOpen] = useState(false)
  const [g, setG] = useState<Gloss | null>(null)
  const [error, setError] = useState(false)

  const toggle = () => {
    setOpen(!open)
    if (!g && !open) load().then(setG).catch(() => setError(true))
  }

  return (
    <section className="mt-4 font-ui">
      <button type="button" onClick={toggle} aria-expanded={open}
        className="flex min-h-10 items-center gap-2 rounded-full border border-line-strong bg-card px-4 text-small text-ink-2 hover:bg-paper-sunken">
        <Languages size={16} /> {open ? 'Hide English' : 'Show in English'} <span className="text-ink-3">· for grown-ups</span>
      </button>
      {open && (
        <div className="mt-3 rounded-xl border-2 border-line bg-card p-4">
          {error ? (
            <p className="m-0 text-small text-ink-3">Translation is not available right now.</p>
          ) : !g ? (
            <DotLoader />
          ) : (
            <ol className="m-0 grid list-none gap-3 p-0">
              {[g.title, ...g.sentences].map((line, i) => (
                <li key={i} className={i === 0 ? 'border-b border-line pb-2' : ''}>
                  <div className="font-story-ne text-body">{line.text}</div>
                  <div className="text-small italic text-ink-2">{line.roman}</div>
                  <div className="text-small">"{line.english}"</div>
                </li>
              ))}
            </ol>
          )}
          <p className="m-0 mt-3 text-caption text-ink-3">Romanised by code; English by AI, for grown-ups only.</p>
        </div>
      )}
    </section>
  )
}
