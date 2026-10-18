import { Sparkles } from 'lucide-react'
import type { components } from '../api-types'
import type { Language } from '../api'
import { sfx } from '../sound'

type Choice = components['schemas']['ChoiceOut']

// "Which story today?" Three picture tiles, all stories this child can read. The child
// picks by picture; the small label is for the adult. The prepared one opens instantly.
export function StoryChoice({ lang, choices, onPick }: { lang: Language; choices: Choice[]; onPick: (theme: string) => void }) {
  const isNe = lang === 'ne'
  return (
    <section className="mx-auto w-full max-w-story">
      <h1 className={`m-0 mb-6 text-center ${isNe ? 'font-story-ne' : 'font-story-en'} text-child-title font-bold`}>
        {isNe ? 'आज कुन कथा?' : 'Which story today?'}
      </h1>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {choices.map((c) => (
          <button
            key={c.theme}
            type="button"
            onClick={() => {
              sfx.pop()
              onPick(c.theme)
            }}
            className="relative flex flex-row items-center gap-4 rounded-2xl border-2 border-b-4 border-line bg-card p-3 text-left transition-colors duration-150 hover:bg-paper-sunken active:translate-y-1 sm:flex-col sm:text-center"
          >
            {c.ready && (
              <span className="absolute right-2 top-2 flex items-center gap-1 rounded-full bg-sun px-2 py-0.5 text-caption font-semibold text-on-sun">
                <Sparkles size={14} /> {isNe ? 'तयार' : 'ready'}
              </span>
            )}
            <img src={c.picture_url} alt="" className="size-24 shrink-0 rounded-xl object-cover sm:size-36" />
            <span>
              <span className="block font-story-ne text-child-label font-semibold">{c.label_ne}</span>
              <span className="block text-small text-ink-3">{c.label_en}</span>
            </span>
          </button>
        ))}
      </div>
    </section>
  )
}
