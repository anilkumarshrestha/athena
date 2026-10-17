import { useState, type ReactNode } from 'react'
import type { Story } from '../api'
import { DotLoader } from '../components/DotLoader'
import { MasteryGrid } from '../components/MasteryGrid'
import { RecordButton, StoryCard } from '../components/StoryCard'
import { UnitChip } from '../components/UnitChip'
import { VerifierLog } from '../components/VerifierLog'
import { WordToken, type Outcome } from '../components/WordToken'

// DESIGN.md §6: every signature component, every state, on dummy data.
// Screens compose these; if it is not here, it is not in the system yet.

const SWATCHES: [string, string][] = [
  ['paper', 'bg-paper'],
  ['paper-sunken', 'bg-paper-sunken'],
  ['card', 'bg-card'],
  ['line', 'bg-line'],
  ['line-strong', 'bg-line-strong'],
  ['ink', 'bg-ink'],
  ['ink-2', 'bg-ink-2'],
  ['ink-3', 'bg-ink-3'],
  ['ink-4', 'bg-ink-4'],
  ['primary', 'bg-primary'],
  ['primary-soft', 'bg-primary-soft'],
  ['crimson', 'bg-crimson'],
  ['correct', 'bg-correct'],
  ['substituted', 'bg-substituted'],
  ['omitted', 'bg-omitted'],
  ['selfcorrected', 'bg-selfcorrected'],
  ['inserted', 'bg-inserted'],
]

const OUTCOMES: Outcome[] = ['pending', 'correct', 'substituted', 'omitted', 'self_corrected']

const NE_LINE: [string, Outcome][] = [
  ['सीता', 'correct'],
  ['खेतमा', 'correct'],
  ['गई।', 'self_corrected'],
  ['त्यहाँ', 'substituted'],
  ['सानो', 'correct'],
  ['बाख्रा', 'omitted'],
  ['थियो।', 'pending'],
]

const EN_LINE: [string, Outcome][] = [
  ['Sam', 'correct'],
  ['sat', 'correct'],
  ['in', 'omitted'],
  ['the', 'self_corrected'],
  ['ship.', 'substituted'],
]

const c = (s: string) => s.split(' ').map((u) => 'c:' + u)
const NE_ALL = c('अ आ इ ई उ ऊ ए ऐ ओ औ क ख ग घ च छ ज झ ट ठ ड ढ ण त थ द ध न प फ ब भ म य र ल व श ष स ह')
const NE_MASTERED = [...NE_ALL, ...'ा ि ी ु ू े ै ो ं ँ ्'.split(' ').map((m) => 'm:' + m), 'k:त्र']
const NE_PRACTICING = ['c:ढ', 'c:ष', 'c:ऋ', 'm:ृ']
const NE_EXCLUDED = ['c:ङ', 'c:ञ']
const NE_CHANGED = { 'c:ढ': 'demoted', 'm:ू': 'promoted' } as const

const EN_MASTERED = [...'s a t p i n m d g o sh'.split(' ').map((g) => 'g:' + g), 'w:a', 'w:the', 'w:i']
const EN_PRACTICING = ['g:c', 'g:k', 'g:ck']

const SAMPLE_STORY: Story = {
  id: 'demo',
  learner_id: 'sita',
  language: 'ne',
  theme: 'goat in the field',
  title: 'सानो बाख्रा',
  sentences: ['सीता खेतमा गई।', 'त्यहाँ एउटा सानो बाख्रा थियो।', 'बाख्राले घाँस खायो।'],
  display: [], // empty: StoryCard falls back to splitting sentences
  letters: [], // letter mode only
  outcome: 'verified',
  units_used: ['c:स', 'm:ी', 'c:त', 'c:ख', 'm:े', 'c:म', 'c:ग', 'c:ब', 'm:ा', 'k:ख्र', 'c:थ', 'm:ि', 'c:य', 'm:ो', 'c:घ', 'm:ँ'],
  attempts: [
    {
      n: 1,
      title: 'सानो बाख्रा',
      sentences: ['सीता क्षेत्रमा गई।', 'त्यहाँ एउटा सुन्दर बाख्रा थियो।', 'बाख्राले फूल खायो।'],
      violations: [
        { word: 'क्षेत्रमा', unit: 'k:क्ष', index: 3, reason: 'not mastered' },
        { word: 'सुन्दर', unit: 'k:न्द', index: 7, reason: 'not mastered' },
        { word: 'फूल', unit: 'm:ू', index: 11, reason: 'not mastered' },
      ],
      ms: 1240,
      model: 'gemini-3-flash',
    },
    {
      n: 2,
      title: 'सानो बाख्रा',
      sentences: ['सीता खेतमा गई।', 'त्यहाँ एउटा सानो बाख्रा थियो।', 'बाख्राले घाँस खायो।'],
      violations: [],
      ms: 980,
      model: 'gemini-3-flash',
    },
  ],
  total_latency_ms: 2220,
  image_status: 'pending',
  image_url: null,
  image_latency_ms: null,
}

function Section({ id, title, children }: { id: string; title: string; children: ReactNode }) {
  return (
    <section id={id} className="border-t border-line py-8">
      <h2 className="mb-6 text-h2 font-semibold">{title}</h2>
      {children}
    </section>
  )
}

function Panel({ label, children }: { label?: string; children: ReactNode }) {
  return (
    <div className="rounded-md border border-line bg-card p-4">
      {label && <div className="mb-3 text-caption text-ink-3">{label}</div>}
      {children}
    </div>
  )
}

export function Styleguide() {
  const [tapped, setTapped] = useState<string | null>(null)

  return (
    <main className="mx-auto box-content max-w-page px-4 py-8 md:px-8">
      <header className="mb-8">
        <h1 className="m-0 text-display font-semibold">Athena styleguide</h1>
        <p className="mt-2 text-body text-ink-3">
          DESIGN.md §6 components on dummy data. Use your browser's print preview to check grayscale.
        </p>
      </header>

      <Section id="color" title="Color">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-6">
          {SWATCHES.map(([name, cls]) => (
            <div key={name} className="overflow-hidden rounded-md border border-line bg-card">
              <div className={`h-12 ${cls}`} />
              <div className="px-2 py-1.5 font-mono text-caption text-ink-2">{name}</div>
            </div>
          ))}
        </div>
      </Section>

      <Section id="type" title="Type">
        <div className="grid gap-4 md:grid-cols-2">
          <Panel label="story-xl · Baloo 2">
            <p className="m-0 font-story-ne text-story-xl font-medium">क्षेत्र श्री कृषि फूल</p>
          </Panel>
          <Panel label="story-xl · Andika">
            <p className="m-0 font-story-en text-story-xl">a g ship Ill1</p>
          </Panel>
          <Panel label="adult scale · IBM Plex">
            <div className="text-display font-semibold">display 32</div>
            <div className="text-h2 font-semibold">h2 20 · शीर्षक</div>
            <div className="text-h3 font-semibold">h3 16</div>
            <div className="text-body">body 14 · बच्चाले क्षेत्र पढ्यो</div>
            <div className="text-caption text-ink-3">caption 12</div>
          </Panel>
          <Panel label="mono · stat">
            <div className="font-mono text-stat tabular-nums">0.00%</div>
            <div className="font-mono text-mono text-ink-2">attempt 2 · 980 ms · 0 violations</div>
          </Panel>
        </div>
      </Section>

      <Section id="word" title="WordToken (§6.1)">
        <div className="grid gap-4 md:grid-cols-2">
          <Panel label="outcomes · ne">
            <div className="flex flex-wrap gap-x-8 gap-y-4 text-story-md">
              {OUTCOMES.map((o) => (
                <span key={o} className="flex flex-col items-start">
                  <WordToken text="क्षेत्र" lang="ne" outcome={o} />
                  <span className="font-ui text-caption text-ink-3">{o}</span>
                </span>
              ))}
            </div>
          </Panel>
          <Panel label="outcomes · en">
            <div className="flex flex-wrap gap-x-8 gap-y-4 text-story-md">
              {OUTCOMES.map((o) => (
                <span key={o} className="flex flex-col items-start">
                  <WordToken text="ship" lang="en" outcome={o} />
                  <span className="font-ui text-caption text-ink-3">{o}</span>
                </span>
              ))}
            </div>
          </Panel>
          <Panel label="after reading · tap a word">
            <p className="story-spacing m-0 text-story-md">
              {NE_LINE.map(([w, o], i) => (
                <span key={i}>
                  {i > 0 && ' '}
                  <WordToken text={w} lang="ne" outcome={o} onTap={() => setTapped(w)} />
                </span>
              ))}
            </p>
            <div className="mt-2 font-mono text-caption text-ink-3">tapped: {tapped ?? '—'}</div>
          </Panel>
          <Panel label="active word">
            <p className="story-spacing m-0 text-story-md">
              {EN_LINE.map(([w], i) => (
                <span key={i}>
                  {i > 0 && ' '}
                  <WordToken text={w} lang="en" active={i === 2} />
                </span>
              ))}
            </p>
          </Panel>
        </div>
      </Section>

      <Section id="chip" title="UnitChip (§6.2)">
        <div className="grid gap-4 md:grid-cols-2">
          <Panel label="sm · states">
            <div className="flex flex-wrap gap-2">
              <UnitChip unit="c:क" state="mastered" />
              <UnitChip unit="c:ढ" state="practicing" />
              <UnitChip unit="c:ङ" state="unseen" />
              <UnitChip unit="c:ञ" state="excluded" />
              <UnitChip unit="m:ु" state="mastered" />
              <UnitChip unit="k:क्ष" state="practicing" />
              <UnitChip unit="g:igh" state="mastered" lang="en" />
              <UnitChip unit="g:a_e" state="unseen" lang="en" />
              <UnitChip unit="w:said" state="mastered" lang="en" />
            </div>
          </Panel>
          <Panel label="sm · changed">
            <div className="flex flex-wrap gap-3">
              <UnitChip unit="m:ू" state="mastered" changed="promoted" />
              <UnitChip unit="c:ढ" state="practicing" changed="demoted" />
            </div>
          </Panel>
          <Panel label="lg · child">
            <div className="flex flex-wrap gap-3">
              <UnitChip unit="c:क" state="mastered" size="lg" />
              <UnitChip unit="c:ढ" state="practicing" size="lg" changed="demoted" />
              <UnitChip unit="c:ङ" state="unseen" size="lg" />
              <UnitChip unit="c:ञ" state="excluded" size="lg" />
              <UnitChip unit="g:sh" state="mastered" size="lg" lang="en" />
            </div>
          </Panel>
        </div>
      </Section>

      <Section id="grid" title="MasteryGrid (§6.3)">
        <div className="grid gap-4 lg:grid-cols-2">
          <Panel label="ne · sm · 2 excluded, 4 practicing, 2 changed">
            <MasteryGrid
              lang="ne"
              mastered={NE_MASTERED}
              practicing={NE_PRACTICING}
              excluded={NE_EXCLUDED}
              changed={NE_CHANGED}
            />
          </Panel>
          <Panel label="en · sm">
            <MasteryGrid lang="en" mastered={EN_MASTERED} practicing={EN_PRACTICING} />
          </Panel>
          <Panel label="ne · lg · child">
            <MasteryGrid
              lang="ne"
              size="lg"
              mastered={NE_MASTERED}
              practicing={NE_PRACTICING}
              excluded={NE_EXCLUDED}
              changed={NE_CHANGED}
            />
          </Panel>
        </div>
      </Section>

      <Section id="log" title="VerifierLog (§6.4)">
        <VerifierLog story={SAMPLE_STORY} />
      </Section>

      <Section id="story" title="StoryCard (§6.5)">
        <StoryCard
          lang="ne"
          title={SAMPLE_STORY.title}
          sentences={SAMPLE_STORY.sentences}
          imageStatus="pending"
          footer={<RecordButton />}
        />
      </Section>

      <Section id="misc" title="Loaders">
        <Panel>
          <DotLoader />
        </Panel>
      </Section>
    </main>
  )
}
