import { Mic, Square } from 'lucide-react'
import { Fragment, type ReactNode } from 'react'
import type { DisplayWord, Language } from '../api'
import { DotLoader } from './DotLoader'
import { WordToken, type Outcome } from './WordToken'

// A shown word can cover several reference words (म्याउँ-म्याउँ): show the worst.
const SEVERITY: Outcome[] = ['pending', 'correct', 'self_corrected', 'substituted', 'omitted']
function worst(indices: number[], outcomes?: Map<number, Outcome>): Outcome {
  if (!outcomes) return 'pending'
  return indices.reduce<Outcome>((acc, i) => {
    const o = outcomes.get(i) ?? 'pending'
    return SEVERITY.indexOf(o) > SEVERITY.indexOf(acc) ? o : acc
  }, 'pending')
}

export function StoryCard({
  lang,
  title,
  sentences,
  imageUrl,
  imageStatus,
  display,
  outcomes,
  wordPractice = false,
  footer,
}: {
  lang: Language
  title?: string
  sentences?: string[]
  imageUrl?: string | null
  imageStatus?: string
  display?: DisplayWord[][]
  outcomes?: Map<number, Outcome>
  wordPractice?: boolean // last-resort fallback: separate words, not a sentence
  footer?: ReactNode
}) {
  const lines: DisplayWord[][] | undefined =
    (display?.length ? display : undefined) ??
    sentences?.map((s) => s.split(/\s+/).filter(Boolean).map((text) => ({ text, indices: [] })))

  return (
    <article className="relative mx-auto w-full max-w-story rounded-lg border border-line bg-card">
      <span className="absolute left-4 top-4 z-10 rounded-full bg-paper-sunken px-3 py-1 text-caption text-ink-2">
        {lang === 'ne' ? 'ने' : 'EN'}
      </span>

      <div className="flex aspect-4/3 items-center justify-center overflow-hidden rounded-t-lg bg-paper-sunken">
        {imageUrl ? (
          <img src={imageUrl} alt="" className="size-full object-cover" />
        ) : imageStatus === 'failed' ? null : (
          <DotLoader label="Drawing the picture" />
        )}
      </div>

      <div className="p-8">
        {lines ? (
          <>
            {title && (
              <h1 className={`mb-4 text-child-title font-semibold ${lang === 'ne' ? 'font-story-ne' : 'font-story-en'}`}>
                {title}
              </h1>
            )}
            <div className="story-spacing text-story-md md:text-story-lg lg:text-story-xl">
              {lines.map((line, i) => (
                <p key={i} className={wordPractice ? 'm-0 flex flex-wrap gap-x-8 gap-y-2' : 'm-0'}>
                  {line.map((w, j) => (
                    // Real space text nodes: word-spacing needs them to act on.
                    <Fragment key={j}>
                      {j > 0 && ' '}
                      <WordToken text={w.text} lang={lang} outcome={worst(w.indices, outcomes)} />
                    </Fragment>
                  ))}
                </p>
              ))}
            </div>
          </>
        ) : (
          <div className="flex min-h-48 items-center justify-center">
            <DotLoader label="Writing your story" />
          </div>
        )}
      </div>

      <div className="relative flex items-center justify-center px-8 pb-8">{footer}</div>
    </article>
  )
}

export type RecordState = 'idle' | 'recording' | 'checking'

export function RecordButton({
  state = 'idle',
  disabled,
  onClick,
}: {
  state?: RecordState
  disabled?: boolean
  onClick?: () => void
}) {
  const label = state === 'recording' ? 'Stop reading' : state === 'checking' ? 'Checking' : 'Read aloud'
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled || state === 'checking'}
      aria-label={label}
      className="flex size-24 items-center justify-center rounded-full bg-primary text-on-primary transition-colors duration-150 hover:bg-primary-hover disabled:bg-ink-4"
      // §4: slow 1.6s ring pulse while listening
      style={state === 'recording' ? { animation: 'ring-pulse 1.6s ease-in-out infinite' } : undefined}
    >
      {state === 'recording' ? (
        <Square size={36} strokeWidth={1.75} fill="currentColor" />
      ) : state === 'checking' ? (
        <span className="[&_span]:bg-on-primary">
          <DotLoader label="Checking" />
        </span>
      ) : (
        <Mic size={40} strokeWidth={1.75} />
      )}
    </button>
  )
}
