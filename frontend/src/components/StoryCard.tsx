import { Mic } from 'lucide-react'
import { Fragment, type ReactNode } from 'react'
import type { Language } from '../api'
import { DotLoader } from './DotLoader'
import { WordToken } from './WordToken'

export function StoryCard({
  lang,
  title,
  sentences,
  imageUrl,
  imageStatus,
  footer,
}: {
  lang: Language
  title?: string
  sentences?: string[]
  imageUrl?: string | null
  imageStatus?: string
  footer?: ReactNode
}) {
  return (
    <article className="relative mx-auto w-full max-w-[720px] rounded-lg border border-line bg-card">
      <span className="absolute left-4 top-4 z-10 rounded-full bg-paper-sunken px-3 py-1 text-caption text-ink-2">
        {lang === 'ne' ? 'ने' : 'EN'}
      </span>

      <div className="flex aspect-[4/3] items-center justify-center overflow-hidden rounded-t-lg bg-paper-sunken">
        {imageUrl ? (
          <img src={imageUrl} alt="" className="size-full object-cover" />
        ) : imageStatus === 'failed' ? null : (
          <DotLoader label="Drawing the picture" />
        )}
      </div>

      <div className="p-8">
        {sentences ? (
          <>
            {title && (
              <h1 className={`mb-4 text-child-title font-semibold ${lang === 'ne' ? 'font-story-ne' : 'font-story-en'}`}>
                {title}
              </h1>
            )}
            <div className="text-story-md [word-spacing:0.3em] md:text-story-lg lg:text-story-xl">
              {sentences.map((s, i) => (
                <p key={i} className="m-0">
                  {s.split(/\s+/).filter(Boolean).map((w, j) => (
                    // Real space text nodes: word-spacing needs them to act on.
                    <Fragment key={j}>
                      {j > 0 && ' '}
                      <WordToken text={w} lang={lang} />
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

export function RecordButton({ disabled, onClick }: { disabled?: boolean; onClick?: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label="Read aloud"
      className="flex size-24 items-center justify-center rounded-full bg-primary text-on-primary transition-colors duration-150 hover:bg-primary-hover disabled:bg-ink-4"
    >
      <Mic size={40} strokeWidth={1.75} />
    </button>
  )
}
