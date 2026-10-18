import { Mic, Square } from 'lucide-react'
import { Fragment, type ReactNode, useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
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
  onWordTap,
  selectedWord = null,
  wordPopover,
  onDismiss,
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
  onWordTap?: (index: number) => void // re-teach: hear / see parts / try again
  selectedWord?: number | null // highlighted word (first reference index)
  wordPopover?: ReactNode // floats above the selected word
  onDismiss?: () => void // Escape / tap outside
  footer?: ReactNode
}) {
  const card = useRef<HTMLElement>(null)
  const lines: DisplayWord[][] | undefined =
    (display?.length ? display : undefined) ??
    sentences?.map((s) => s.split(/\s+/).filter(Boolean).map((text) => ({ text, indices: [] })))

  return (
    <article ref={card} className="relative mx-auto w-full max-w-story rounded-xl border-2 border-sky bg-card">
      <span className="absolute left-4 top-4 z-10 rounded-full bg-sun px-3 py-1 text-caption font-semibold text-on-sun">
        {lang === 'ne' ? 'ने' : 'EN'}
      </span>

      <div className="flex aspect-4/3 items-center justify-center overflow-hidden rounded-t-xl bg-sky-soft">
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
                      <WordToken
                        text={w.text}
                        lang={lang}
                        outcome={worst(w.indices, outcomes)}
                        dataWord={w.indices[0]}
                        selected={selectedWord !== null && w.indices.includes(selectedWord)}
                        onTap={onWordTap && w.indices.length ? () => onWordTap(w.indices[0]) : undefined}
                      />
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

      {wordPopover && selectedWord !== null && (
        <WordPopover card={card} word={selectedWord} onDismiss={onDismiss}>
          {wordPopover}
        </WordPopover>
      )}
    </article>
  )
}

const GAP = 12 // space between word and popover
const EDGE = 8 // keep clear of the card edge

// Floats above the selected word (below if there is no room), arrow pointing at it.
function WordPopover({
  card,
  word,
  onDismiss,
  children,
}: {
  card: React.RefObject<HTMLElement | null>
  word: number
  onDismiss?: () => void
  children: ReactNode
}) {
  const box = useRef<HTMLDivElement>(null)
  const [pos, setPos] = useState<{ left: number; top: number; arrow: number; below: boolean } | null>(null)

  const place = useCallback(() => {
    const c = card.current
    const b = box.current
    const w = c?.querySelector<HTMLElement>(`[data-word="${word}"]`)
    if (!c || !b || !w) return
    const cr = c.getBoundingClientRect()
    const wr = w.getBoundingClientRect()
    const cx = wr.left + wr.width / 2 - cr.left
    const left = Math.min(Math.max(cx - b.offsetWidth / 2, EDGE), cr.width - b.offsetWidth - EDGE)
    const below = wr.top - b.offsetHeight - GAP < 0
    const top = below ? wr.bottom - cr.top + GAP : wr.top - cr.top - b.offsetHeight - GAP
    const arrow = Math.min(Math.max(cx - left, 20), b.offsetWidth - 20)
    setPos({ left, top, arrow, below })
  }, [card, word])

  useLayoutEffect(place, [place])
  useEffect(() => {
    // Content grows as help loads (picture, parts): re-place when it does.
    const ro = new ResizeObserver(place)
    if (box.current) ro.observe(box.current)
    window.addEventListener('resize', place)
    return () => {
      ro.disconnect()
      window.removeEventListener('resize', place)
    }
  }, [place])

  useEffect(() => {
    if (pos) box.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  }, [pos?.below, word]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const key = (e: KeyboardEvent) => e.key === 'Escape' && onDismiss?.()
    const down = (e: PointerEvent) => {
      const t = e.target as HTMLElement
      if (!box.current?.contains(t) && !t.closest('[data-word]')) onDismiss?.()
    }
    document.addEventListener('keydown', key)
    document.addEventListener('pointerdown', down)
    return () => {
      document.removeEventListener('keydown', key)
      document.removeEventListener('pointerdown', down)
    }
  }, [onDismiss])

  return (
    <div
      ref={box}
      role="dialog"
      aria-label="Word help"
      style={{ left: pos?.left ?? 0, top: pos?.top ?? 0, visibility: pos ? 'visible' : 'hidden' }}
      className="absolute z-20 w-80 max-w-[calc(100%-1rem)] rounded-2xl border-2 border-primary bg-card p-4 shadow-float"
    >
      {children}
      <span
        aria-hidden
        style={{ left: (pos?.arrow ?? 0) - 8 }}
        className={`absolute size-4 rotate-45 border-primary bg-card ${
          pos?.below ? '-top-2.5 border-l-2 border-t-2' : '-bottom-2.5 border-b-2 border-r-2'
        }`}
      />
    </div>
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
      className="flex size-24 items-center justify-center rounded-full border-b-4 border-leaf-edge bg-leaf text-on-primary transition-colors duration-150 hover:bg-leaf-edge active:translate-y-1 active:border-b-0 disabled:border-ink-3 disabled:bg-ink-4"
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
