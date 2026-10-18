import { ArrowLeft, ArrowRight, Moon, Square, Volume2 } from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api, type CloseResult, type Language, type ReadResult, type Story } from '../api'
import { ReadingLog } from '../components/ReadingLog'
import { LetterPractice } from '../components/LetterPractice'
import { ReteachPanel } from '../components/ReteachPanel'
import { RecordButton, StoryCard } from '../components/StoryCard'
import { VerifierLog } from '../components/VerifierLog'
import { UnitChip } from '../components/UnitChip'
import type { Outcome } from '../components/WordToken'
import { useLiveFollow } from '../hooks/useLiveFollow'
import { useNarration } from '../hooks/useNarration'
import { useRecorder } from '../hooks/useRecorder'
import { sfx } from '../sound'

const POLL_MS = 1500

const PRAISE = {
  ne: { great: 'धेरै राम्रो पढ्यौ!', good: 'राम्रो पढ्यौ! अझ अभ्यास गरौँ।', try: 'राम्रो प्रयास! सँगै फेरि पढौँ।' },
  en: { great: 'Great reading!', good: "Good reading! Let's practise a little more.", try: "Good try! Let's read it together again." },
} as const

export function StoryScreen({ learnerId, lang, onBack }: { learnerId: string; lang: Language; onBack: () => void }) {
  const [story, setStory] = useState<Story | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [showLog, setShowLog] = useState(false)
  const [reading, setReading] = useState<ReadResult | null>(null)
  const [closed, setClosed] = useState<CloseResult | null>(null)
  const [helpWord, setHelpWord] = useState<number | null>(null)
  const [praise, setPraise] = useState<'great' | 'good' | 'try' | null>(null)
  const [fixed, setFixed] = useState<Set<number>>(new Set()) // words got right on a retry
  const [checking, setChecking] = useState(false)
  const recorder = useRecorder()
  const live = useLiveFollow(story?.id || undefined)
  const narration = useNarration(story?.id || undefined)
  const reqId = useRef(0)

  const load = useCallback(() => {
    const id = ++reqId.current
    setStory(null)
    setReading(null)
    setClosed(null)
    setHelpWord(null)
    setPraise(null)
    setFixed(new Set())
    setError(null)
    api
      .startSession(learnerId, lang)
      .then((s) => id === reqId.current && setStory(s))
      .catch((e) => id === reqId.current && setError(String(e.message ?? e)))
  }, [learnerId, lang])

  useEffect(load, [load])

  // Image is generated in parallel; poll until it lands.
  useEffect(() => {
    if (!story || story.image_status !== 'pending') return
    const t = setTimeout(() => {
      api.story(story.id).then((s) => s.id === story.id && setStory(s)).catch(() => {})
    }, POLL_MS)
    return () => clearTimeout(t)
  }, [story])

  const outcomes = useMemo(
    () =>
      reading
        ? new Map(
            reading.words.map((w) => [w.index, (fixed.has(w.index) ? 'self_corrected' : w.outcome) as Outcome]),
          )
        : undefined,
    [reading, fixed],
  )

  const onRecord = async () => {
    if (!story) return
    if (recorder.state !== 'recording') {
      narration.stop() // never read aloud into the microphone
      setReading(null)
      sfx.click()
      await new Promise((r) => setTimeout(r, 120)) // let the click finish before the mic opens
      return recorder.start((stream) => live.start(stream)) // same mic for recording + live guide
    }
    live.stop()
    const { blob, durationS } = await recorder.stop()
    sfx.click() // mic is closed now: safe to play
    setChecking(true)
    try {
      const r = await api.read(story.id, blob, durationS)
      setReading(r)
      // Warm spoken praise, matched to how it went; never a score for the child.
      const acc = r.words.length ? r.words_correct / r.words.length : 0
      const tier = acc >= 0.9 ? 'great' : acc >= 0.6 ? 'good' : 'try'
      setPraise(tier)
      sfx.chime()
      setTimeout(() => new Audio(api.praiseUrl(lang, tier)).play().catch(() => {}), 350) // chime, then praise
      // First reading of a story updates mastery once; later re-reads are practice only.
      if (!closed) {
        const c = await api.closeSession(story.id)
        setClosed(c)
        if (c.changes.some((x) => x.after === 'mastered' || x.before === 'unseen')) setTimeout(sfx.sparkle, 900)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setChecking(false)
    }
  }

  return (
    <main className="mx-auto box-content max-w-story px-4 pb-16 pt-4 md:px-8">
      <button
        type="button"
        onClick={onBack}
        aria-label="Back"
        className="mb-4 flex size-16 items-center justify-center rounded-full text-ink-2 transition-colors duration-150 hover:bg-paper-sunken"
      >
        <ArrowLeft size={32} strokeWidth={1.75} />
      </button>

      {error === 'daily_limit' ? (
        <section className="flex flex-col items-center gap-4 rounded-2xl border-2 border-b-4 border-line bg-card p-12 text-center">
          <Moon size={64} strokeWidth={1.5} className="text-primary" />
          <p className="m-0 font-story-ne text-child-title font-bold">आजलाई यति नै! भोलि फेरि पढौँ।</p>
          <p className="m-0 font-story-en text-child-label text-ink-2">That's all for today. Let's read again tomorrow!</p>
        </section>
      ) : error ? (
        <p className="rounded-lg border border-line bg-card p-8 text-child-label text-omitted">{error}</p>
      ) : story?.outcome === 'letters' ? (
        closed ? (
          <div className="flex justify-center">
            <button type="button" onClick={load} className="flex min-h-16 items-center gap-2 rounded-xl border-2 border-b-4 border-primary-hover bg-primary px-8 text-child-label font-bold text-on-primary">
              {lang === 'ne' ? 'अर्को' : 'Next'} <ArrowRight size={28} />
            </button>
          </div>
        ) : (
          <LetterPractice
            learnerId={learnerId}
            lang={lang}
            cards={(story.letters ?? []) as { unit: string; example: string; practising: boolean }[]}
            onClosed={setClosed}
          />
        )
      ) : (
        <StoryCard
          lang={lang}
          title={story?.title}
          sentences={story?.sentences}
          imageUrl={story?.image_url}
          imageStatus={story?.image_status}
          display={story?.display}
          wordPractice={story?.outcome === 'wordlist'}
          onWordTap={
            story
              ? (i) => {
                  if (recorder.state !== 'recording') sfx.pop() // never into the microphone
                  setHelpWord((cur) => (cur === i ? null : i))
                }
              : undefined
          }
          selectedWord={helpWord}
          onDismiss={() => setHelpWord(null)}
          wordPopover={
            story &&
            helpWord !== null && (
              <ReteachPanel
                key={helpWord}
                storyId={story.id}
                index={helpWord}
                lang={lang}
                onClose={() => setHelpWord(null)}
                onSuccess={(i) => setFixed((f) => new Set(f).add(i))}
              />
            )
          }
          outcomes={outcomes}
          live={
            recorder.state === 'recording'
              ? { heard: live.heard, next: live.next }
              : narration.playing
                ? { heard: new Set<number>(), next: narration.word } // being read TO the child: glow only
                : undefined
          }
          footer={
            // 3 columns so nothing overlaps at phone width: read-to-me | mic | next
            <div className="grid w-full grid-cols-[1fr_auto_1fr] items-center gap-3">
              {story && recorder.state !== 'recording' && !checking ? (
                <button
                  type="button"
                  onClick={narration.playing ? narration.stop : narration.play}
                  aria-label={narration.playing ? 'Stop reading to me' : 'Read to me'}
                  className="flex min-h-16 min-w-16 items-center justify-center gap-2 justify-self-start rounded-xl border-2 border-b-4 border-sky-edge bg-sky-soft px-3 text-child-label font-bold text-ink active:translate-y-1"
                >
                  {narration.playing ? <Square size={26} fill="currentColor" /> : <Volume2 size={28} strokeWidth={2} />}
                  <span className={`hidden sm:inline ${lang === 'ne' ? 'font-story-ne' : 'font-story-en'}`}>{lang === 'ne' ? 'सुनाऊ' : 'Read to me'}</span>
                </button>
              ) : (
                <span />
              )}
              <RecordButton
                state={checking ? 'checking' : recorder.state === 'recording' ? 'recording' : 'idle'}
                disabled={!story}
                onClick={onRecord}
              />
              {story && recorder.state !== 'recording' && !checking ? (
                <button
                  type="button"
                  onClick={load}
                  className="flex min-h-16 items-center gap-1 justify-self-end rounded-lg px-2 text-child-label font-semibold text-primary transition-colors duration-150 hover:bg-primary-soft"
                >
                  {lang === 'ne' ? 'अर्को' : 'Next'}
                  <ArrowRight size={32} strokeWidth={1.75} />
                </button>
              ) : (
                <span />
              )}
            </div>
          }
        />
      )}

      {praise && (
        <p aria-live="polite" className={`mx-auto mt-6 max-w-story text-center ${lang === 'ne' ? 'font-story-ne' : 'font-story-en'} text-child-title font-bold text-ink`}>
          {PRAISE[lang][praise]}
        </p>
      )}

      {closed && closed.changes.length > 0 && (
        <div className="mx-auto mt-4 flex max-w-story flex-col gap-4 rounded-2xl border-2 border-b-4 border-line bg-card p-5">
          {(() => {
            const up = closed.changes.filter((c) => c.after === 'mastered' || c.before === 'unseen')
            const practise = closed.changes.filter((c) => !(c.after === 'mastered' || c.before === 'unseen'))
            const group = (label: string, items: typeof up, changed: 'promoted' | 'demoted') =>
              items.length > 0 && (
                <div>
                  <p className={`m-0 mb-2 ${lang === 'ne' ? 'font-story-ne' : 'font-story-en'} text-child-label font-semibold text-ink-2`}>{label}</p>
                  <div className="flex flex-wrap gap-3">
                    {items.map((c) => (
                      <UnitChip key={c.unit} unit={c.unit} size="lg" lang={lang} state={c.after as 'mastered' | 'practicing'} changed={changed} />
                    ))}
                  </div>
                </div>
              )
            return (
              <>
                {group(lang === 'ne' ? 'नयाँ अक्षर! पढ्न सक्छौ।' : 'New letters you can read!', up, 'promoted')}
                {group(lang === 'ne' ? 'अझ अभ्यास गरौँ:' : "Let's practise these:", practise, 'demoted')}
              </>
            )
          })()}
        </div>
      )}

      {story && story.outcome !== 'letters' && (
        <div className="mt-8">
          <button
            type="button"
            onClick={() => setShowLog((v) => !v)}
            className="mb-3 text-body text-ink-3 underline underline-offset-4 hover:text-ink-2"
          >
            {showLog ? 'Hide' : 'Show'} how this story was made
          </button>
          {showLog && (
            <div className="flex flex-col gap-3">
              {reading && <ReadingLog result={reading} />}
              <VerifierLog story={story} />
            </div>
          )}
          {recorder.error && <p className="mt-3 text-body text-omitted">Microphone: {recorder.error}</p>}
        </div>
      )}
    </main>
  )
}
