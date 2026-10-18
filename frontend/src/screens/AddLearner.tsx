import { ArrowLeft, ArrowRight, Bike, Check, Music, Palette, PartyPopper } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import type { components } from '../api-types'
import { api } from '../api'
import { sfx } from '../sound'

type Create = components['schemas']['LearnerCreate']

// Onboarding, one question per screen (like Duolingo ABC): the reading buddy asks, the
// grown-up and child tap big picture tiles, a bar shows how far along they are. Every answer
// is a fixed choice (they reach the model prompt); first name only, a general setting, no
// exact place (PLAN §11). Then the card check finds where to start.

type Tile<T extends string> = { id: T; ne: string; en: string; pic?: string; icon?: ReactNode }

const pic = (noun: string) => `/api/pictures/ne/${noun}`

const GENDERS: Tile<NonNullable<Create['gender']>>[] = [
  { id: 'boy', ne: 'छोरा', en: 'Boy' },
  { id: 'girl', ne: 'छोरी', en: 'Girl' },
  { id: 'unspecified', ne: 'नभन्ने', en: 'Prefer not to say' },
]
const AGES: Tile<NonNullable<Create['age']>>[] = [
  { id: '4', ne: '४', en: '4' }, { id: '5', ne: '५', en: '5' }, { id: '6', ne: '६', en: '6' },
  { id: '7', ne: '७', en: '7' }, { id: '8', ne: '८+', en: '8+' },
]
const LANGS: Tile<NonNullable<Create['languages']>>[] = [
  { id: 'ne', ne: 'नेपाली', en: 'Nepali' },
  { id: 'en', ne: 'अङ्ग्रेजी', en: 'English' },
  { id: 'both', ne: 'दुवै', en: 'Both' },
]
const ANIMALS: Tile<Create['favorite_animal']>[] = [
  { id: 'goat', ne: 'बाख्रा', en: 'Goat', pic: pic('बाख्रा') },
  { id: 'cat', ne: 'बिरालो', en: 'Cat', pic: pic('बिरालो') },
  { id: 'dog', ne: 'कुकुर', en: 'Dog', pic: pic('कुकुर') },
  { id: 'hen', ne: 'कुखुरा', en: 'Hen', pic: pic('कुखुरा') },
  { id: 'cow', ne: 'गाई', en: 'Cow', pic: pic('गाई') },
  { id: 'buffalo', ne: 'भैंसी', en: 'Buffalo', pic: pic('भैंसी') },
  { id: 'bird', ne: 'चरा', en: 'Bird', pic: pic('चरा') },
  { id: 'yak', ne: 'याक', en: 'Yak', pic: pic('याक') },
]
const FOODS: Tile<Create['favorite_food']>[] = [
  { id: 'dal_bhat', ne: 'दाल भात', en: 'Dal bhat', pic: pic('भात') },
  { id: 'momo', ne: 'मोमो', en: 'Momo', pic: pic('मोमो') },
  { id: 'roti', ne: 'रोटी', en: 'Roti', pic: pic('रोटी') },
  { id: 'mango', ne: 'आँप', en: 'Mango', pic: pic('आँप') },
  { id: 'banana', ne: 'केरा', en: 'Banana', pic: pic('केरा') },
  { id: 'milk', ne: 'दूध', en: 'Milk', pic: pic('दूध') },
  { id: 'corn', ne: 'मकै', en: 'Corn', pic: pic('मकै') },
  { id: 'egg', ne: 'अण्डा', en: 'Egg', pic: pic('अण्डा') },
]
const ACTIVITIES: Tile<NonNullable<Create['activity']>>[] = [
  { id: 'kite', ne: 'चङ्गा उडाउने', en: 'Flying kites', pic: pic('चङ्गा') },
  { id: 'football', ne: 'फुटबल', en: 'Football', pic: pic('बल') },
  { id: 'dancing', ne: 'नाच्ने', en: 'Dancing', icon: <PartyPopper size={48} strokeWidth={1.5} /> },
  { id: 'drawing', ne: 'चित्र कोर्ने', en: 'Drawing', icon: <Palette size={48} strokeWidth={1.5} /> },
  { id: 'singing', ne: 'गीत गाउने', en: 'Singing', icon: <Music size={48} strokeWidth={1.5} /> },
  { id: 'cycling', ne: 'साइकल चलाउने', en: 'Cycling', icon: <Bike size={48} strokeWidth={1.5} /> },
]
const SETTINGS: Tile<Create['setting']>[] = [
  { id: 'hills', ne: 'पहाड', en: 'Hills', pic: pic('पहाड') },
  { id: 'terai', ne: 'तराई', en: 'Terai', pic: pic('खेत') },
  { id: 'mountains', ne: 'हिमाल', en: 'Mountains', pic: pic('हिमाल') },
  { id: 'city', ne: 'सहर', en: 'City', pic: pic('बजार') },
]
const BUDDIES: Tile<NonNullable<Create['buddy']>>[] = [
  { id: 'cat', ne: 'बिरालो', en: 'Cat', pic: pic('बिरालो') },
  { id: 'dog', ne: 'कुकुर', en: 'Dog', pic: pic('कुकुर') },
  { id: 'goat', ne: 'बाख्रा', en: 'Goat', pic: pic('बाख्रा') },
  { id: 'bird', ne: 'चरा', en: 'Bird', pic: pic('चरा') },
  { id: 'rabbit', ne: 'खरायो', en: 'Rabbit', pic: pic('खरायो') },
]
const GOALS: Tile<NonNullable<Create['daily_goal']>>[] = [
  { id: '5', ne: '५ मिनेट · सजिलो', en: '5 min · Easy' },
  { id: '10', ne: '१० मिनेट · नियमित', en: '10 min · Regular' },
  { id: '15', ne: '१५ मिनेट · धेरै', en: '15 min · Keen' },
]

type Answers = {
  nameNe: string; nameEn: string
  gender?: Create['gender']; age?: Create['age']; languages?: Create['languages']
  animal?: Create['favorite_animal']; food?: Create['favorite_food']; activity?: Create['activity']
  setting?: Create['setting']; buddy?: Create['buddy']; goal?: Create['daily_goal']
}

type Step = { key: keyof Answers | 'hello' | 'name' | 'done'; ne: string; en: string }
const STEPS: Step[] = [
  { key: 'hello', ne: 'नमस्ते! म तिम्रो पढ्ने साथी। सँगै पढौँ!', en: "Hi! I'm your reading buddy. Let's read together!" },
  { key: 'name', ne: 'तिम्रो नाम के हो?', en: "What's your name?" },
  { key: 'gender', ne: 'तिमी छोरा कि छोरी?', en: 'Are you a boy or a girl?' },
  { key: 'age', ne: 'तिमी कति वर्षको भयौ?', en: 'How old are you?' },
  { key: 'languages', ne: 'कुन भाषा पढ्न सिक्ने?', en: 'Which language will you learn to read?' },
  { key: 'animal', ne: 'तिमीलाई कुन जनावर मन पर्छ?', en: 'Which animal do you like best?' },
  { key: 'food', ne: 'कुन खाना मन पर्छ?', en: 'Which food do you like best?' },
  { key: 'activity', ne: 'के गर्न मन पर्छ?', en: 'What do you love doing?' },
  { key: 'setting', ne: 'तिमी कहाँ बस्छौ?', en: 'Where do you live?' },
  { key: 'buddy', ne: 'तिम्रो पढ्ने साथी छान!', en: 'Pick your reading buddy!' },
  { key: 'goal', ne: 'दिनमा कति बेर पढ्ने?', en: 'How long will you read each day?' },
  { key: 'done', ne: 'सबै तयार! अब तिमीले कुन अक्षर चिन्छौ, हेरौँ।', en: "All set! Now let's see which letters you know." },
]
const TILES: Partial<Record<Step['key'], Tile<string>[]>> = {
  gender: GENDERS, age: AGES, languages: LANGS, animal: ANIMALS, food: FOODS,
  activity: ACTIVITIES, setting: SETTINGS, buddy: BUDDIES, goal: GOALS,
}
// grown-up notes, small, under the question
const NOTE: Partial<Record<Step['key'], string>> = {
  hello: 'A grown-up helps set this up: about a minute. First name only; every answer is a fixed choice.',
  gender: 'Nepali verbs change with it (राम गयो, सीता गइन्), so stories read right.',
  age: 'The youngest start with the shortest stories.',
  animal: 'Stories will often be about it.',
  activity: 'Stories will sometimes be about it, too.',
  setting: 'Only a general setting, never an exact place.',
  buddy: 'The buddy is on the learner card, and the child teaches it in "Teach the buddy".',
  goal: "The child's own goal, shown on the learner card. The parent's time limit is separate.",
}

export function AddLearner({ onDone, onBack }: { onDone: (learnerId: string, languages: string) => void; onBack: () => void }) {
  const [i, setI] = useState(0)
  const [a, setA] = useState<Answers>({ nameNe: '', nameEn: '' })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const step = STEPS[i]
  const tiles = TILES[step.key]
  const buddyPic = BUDDIES.find((b) => b.id === a.buddy)?.pic ?? pic('बिरालो')
  const nameOk = /^[A-Za-z][A-Za-z ]*$/.test(a.nameEn.trim()) && /^[ऀ-ॿ ]+$/.test(a.nameNe.trim())

  const next = () => setI((n) => Math.min(n + 1, STEPS.length - 1))
  const back = () => (i === 0 ? onBack() : setI(i - 1))

  const pick = (id: string) => {
    setA((x) => ({ ...x, [step.key]: id }))
    sfx.pop()
    setTimeout(next, 280) // one tap answers: on to the next question
  }

  const finish = async () => {
    setSaving(true)
    setError(null)
    try {
      const learner = await api.createLearner({
        name_ne: a.nameNe.trim(),
        name_en: a.nameEn.trim(),
        gender: a.gender ?? 'unspecified',
        age: a.age ?? null,
        languages: a.languages ?? 'both',
        favorite_animal: a.animal ?? 'cat',
        favorite_food: a.food ?? 'dal_bhat',
        activity: a.activity ?? null,
        setting: a.setting ?? 'hills',
        buddy: a.buddy ?? 'cat',
        daily_goal: a.goal ?? '10',
        start: 'beginner', // the card check right after sets the real starting point
      })
      sfx.sparkle()
      onDone(learner.id, a.languages ?? 'both')
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setSaving(false)
    }
  }

  const input = 'min-h-16 w-full rounded-xl border-2 border-line-strong bg-card px-4 text-child-label focus-visible:border-primary'
  const chosen = step.key in a ? (a[step.key as keyof Answers] as string | undefined) : undefined

  return (
    <main className="mx-auto box-content max-w-story px-4 pb-16 pt-4 md:px-8">
      {/* back + progress */}
      <div className="mb-6 flex items-center gap-3">
        <button type="button" onClick={back} aria-label="Back" className="flex size-12 shrink-0 items-center justify-center rounded-full text-ink-2 hover:bg-paper-sunken">
          <ArrowLeft size={28} strokeWidth={1.75} />
        </button>
        <div className="h-4 flex-1 overflow-hidden rounded-full bg-line" role="progressbar" aria-valuemin={0} aria-valuemax={STEPS.length - 1} aria-valuenow={i}>
          <div className="h-full rounded-full bg-primary transition-all duration-300" style={{ width: `${(i / (STEPS.length - 1)) * 100}%` }} />
        </div>
      </div>

      {/* the buddy asks */}
      <div className="mb-6 flex items-center gap-4">
        <div className="size-20 shrink-0 overflow-hidden rounded-full border-4 border-sun bg-paper-sunken">
          <img src={buddyPic} alt="" className="size-full object-cover" />
        </div>
        <div className="rounded-2xl bg-sun-soft px-5 py-3">
          <p className="m-0 font-story-ne text-child-label font-bold">{step.key === 'done' && a.nameNe ? `${a.nameNe}, ${step.ne}` : step.ne}</p>
          <p className="m-0 text-body text-ink-2">{step.en}</p>
        </div>
      </div>
      {NOTE[step.key] && <p className="m-0 mb-6 text-small text-ink-3">{NOTE[step.key]}</p>}

      {step.key === 'hello' && (
        <button type="button" onClick={next} className="flex min-h-16 w-full items-center justify-center gap-2 rounded-xl border-b-4 border-primary-hover bg-primary text-child-label font-bold text-on-primary active:translate-y-1">
          सुरु गरौँ · Start <ArrowRight size={26} />
        </button>
      )}

      {step.key === 'name' && (
        <>
          <div className="mb-6 grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="mb-2 block text-h3 font-semibold">नाम (नेपालीमा)</span>
              <input className={`${input} font-story-ne`} value={a.nameNe} onChange={(e) => setA({ ...a, nameNe: e.target.value })} placeholder="सीता" lang="ne" maxLength={20} />
            </label>
            <label className="block">
              <span className="mb-2 block text-h3 font-semibold">Name (English)</span>
              <input className={`${input} font-story-en`} value={a.nameEn} onChange={(e) => setA({ ...a, nameEn: e.target.value })} placeholder="Sita" maxLength={20} />
            </label>
          </div>
          <button type="button" disabled={!nameOk} onClick={next}
            className="flex min-h-16 w-full items-center justify-center gap-2 rounded-xl border-b-4 border-primary-hover bg-primary text-child-label font-bold text-on-primary active:translate-y-1 disabled:border-ink-3 disabled:bg-ink-4">
            अगाडि · Next <ArrowRight size={26} />
          </button>
          <p className="m-0 mt-2 text-small text-ink-3">First name only. Nepali in Devanagari, English in letters A–Z.</p>
        </>
      )}

      {tiles && (
        <div role="radiogroup" className={`grid gap-3 ${tiles.length > 4 ? 'grid-cols-2 sm:grid-cols-3' : tiles.length === 3 ? 'grid-cols-1 sm:grid-cols-3' : 'grid-cols-2'}`}>
          {tiles.map((t) => {
            const on = chosen === t.id
            return (
              <button key={t.id} type="button" role="radio" aria-checked={on} onClick={() => pick(t.id)}
                className={`relative flex min-h-20 flex-col items-center justify-center gap-2 rounded-2xl border-2 border-b-4 p-3 text-center transition-colors duration-150 active:translate-y-1 ${
                  on ? 'border-primary bg-primary-soft' : 'border-line-strong bg-card hover:bg-paper-sunken'}`}>
                {on && <Check size={22} className="absolute right-2 top-2 text-primary" />}
                {t.pic && <img src={t.pic} alt="" className="size-20 rounded-xl object-cover" />}
                {t.icon && <span className="flex size-20 items-center justify-center text-ink-2">{t.icon}</span>}
                <span className="font-story-ne text-child-label font-bold">{t.ne}</span>
                <span className="text-small text-ink-3">{t.en}</span>
              </button>
            )
          })}
        </div>
      )}
      {tiles && chosen && (
        <div className="mt-4 flex justify-end">
          <button type="button" onClick={next} className="flex min-h-14 items-center gap-2 rounded-xl px-4 text-child-label font-semibold text-primary">
            अगाडि · Next <ArrowRight size={24} />
          </button>
        </div>
      )}

      {step.key === 'done' && (
        <>
          <ul className="m-0 mb-6 grid list-none grid-cols-2 gap-2 p-0 text-small text-ink-2 sm:grid-cols-3">
            {[
              ['नाम', `${a.nameNe} · ${a.nameEn}`],
              ['जनावर', ANIMALS.find((x) => x.id === a.animal)?.ne],
              ['खाना', FOODS.find((x) => x.id === a.food)?.ne],
              ['मन पर्ने काम', ACTIVITIES.find((x) => x.id === a.activity)?.ne],
              ['भाषा', LANGS.find((x) => x.id === a.languages)?.ne],
              ['लक्ष्य', GOALS.find((x) => x.id === a.goal)?.ne],
            ].filter(([, v]) => v).map(([k, v]) => (
              <li key={k} className="rounded-lg border border-line bg-card px-3 py-2">
                <span className="text-ink-3">{k}: </span><span className="font-story-ne text-ink">{v}</span>
              </li>
            ))}
          </ul>
          {error && <p className="mb-4 text-body text-omitted">{error}</p>}
          <button type="button" disabled={saving || !nameOk} onClick={finish}
            className="flex min-h-16 w-full items-center justify-center gap-2 rounded-xl border-b-4 border-primary-hover bg-primary text-child-label font-bold text-on-primary active:translate-y-1 disabled:bg-ink-4">
            {saving ? '…' : 'अक्षर खेल सुरु गरौँ · Start the letter game'} <ArrowRight size={26} />
          </button>
        </>
      )}
    </main>
  )
}
