import { ArrowLeft } from 'lucide-react'
import { useState } from 'react'
import type { components } from '../api-types'
import { api } from '../api'

type Create = components['schemas']['LearnerCreate']

// Filled in by a parent or teacher. Fixed choices only (they reach the model prompt);
// a general setting, never an exact village (PLAN §11: avatar + first name only).
const ANIMALS: [Create['favorite_animal'], string, string][] = [
  ['goat', 'बाख्रा', 'Goat'],
  ['cat', 'बिरालो', 'Cat'],
  ['dog', 'कुकुर', 'Dog'],
  ['hen', 'कुखुरा', 'Hen'],
  ['cow', 'गाई', 'Cow'],
  ['buffalo', 'भैंसी', 'Buffalo'],
  ['bird', 'चरा', 'Bird'],
  ['yak', 'याक', 'Yak'],
]
const FOODS: [Create['favorite_food'], string, string][] = [
  ['dal_bhat', 'दाल भात', 'Dal bhat'],
  ['momo', 'मोमो', 'Momo'],
  ['roti', 'रोटी', 'Roti'],
  ['mango', 'आँप', 'Mango'],
  ['banana', 'केरा', 'Banana'],
  ['milk', 'दूध', 'Milk'],
  ['corn', 'मकै', 'Corn'],
  ['egg', 'अण्डा', 'Egg'],
]
const SETTINGS: [Create['setting'], string, string][] = [
  ['hills', 'पहाड', 'Hills'],
  ['terai', 'तराई', 'Terai'],
  ['mountains', 'हिमाल', 'Mountains'],
  ['city', 'सहर', 'City'],
]
function Choice<T extends string>({
  label,
  options,
  value,
  onChange,
}: {
  label: string
  options: [T, string, string][]
  value: T | null
  onChange: (v: T) => void
}) {
  return (
    <fieldset className="m-0 mb-8 border-0 p-0">
      <legend className="mb-3 text-h3 font-semibold">{label}</legend>
      <div role="radiogroup" className="flex flex-wrap gap-3">
        {options.map(([id, ne, en]) => (
          <button
            key={id}
            type="button"
            role="radio"
            aria-checked={value === id}
            onClick={() => onChange(id)}
            className={`min-h-16 rounded-xl border-2 px-5 py-2 text-left transition-colors duration-150 ${
              value === id ? 'border-primary border-b-4 bg-primary-soft' : 'border-line-strong border-b-4 bg-card hover:bg-paper-sunken'
            }`}
          >
            <span className="block font-story-ne text-child-label font-semibold">{ne}</span>
            <span className="block text-small text-ink-3">{en}</span>
          </button>
        ))}
      </div>
    </fieldset>
  )
}

export function AddLearner({ onDone, onBack }: { onDone: (learnerId: string) => void; onBack: () => void }) {
  const [nameNe, setNameNe] = useState('')
  const [nameEn, setNameEn] = useState('')
  const [animal, setAnimal] = useState<Create['favorite_animal'] | null>(null)
  const [food, setFood] = useState<Create['favorite_food'] | null>(null)
  const [setting, setSetting] = useState<Create['setting'] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const ready = nameNe.trim() && nameEn.trim() && animal && food && setting

  const submit = async () => {
    if (!ready) return
    setSaving(true)
    setError(null)
    try {
      const learner = await api.createLearner({
        name_ne: nameNe.trim(),
        name_en: nameEn.trim(),
        favorite_animal: animal,
        favorite_food: food,
        setting,
        start: 'beginner', // the card check right after sets the real starting point
      })
      onDone(learner.id)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setSaving(false)
    }
  }

  const input =
    'min-h-16 w-full rounded-lg border border-line-strong bg-card px-4 text-child-label focus-visible:border-primary'

  return (
    <main className="mx-auto box-content max-w-story px-4 py-8 md:px-8">
      <button type="button" onClick={onBack} className="mb-6 flex items-center gap-2 text-body text-ink-2 hover:text-ink">
        <ArrowLeft size={20} strokeWidth={1.75} /> Learners
      </button>
      <h1 className="m-0 mb-2 font-story-ne text-child-title font-bold">नयाँ साथी</h1>
      <p className="m-0 mb-8 text-body text-ink-3">
        For a parent or teacher. First name only; favourites make the stories feel like the child's own. Next: a 2-minute card check to find where to start.
      </p>

      <div className="mb-8 grid gap-4 sm:grid-cols-2">
        <label className="block">
          <span className="mb-2 block text-h3 font-semibold">नाम (नेपालीमा)</span>
          <input className={`${input} font-story-ne`} value={nameNe} onChange={(e) => setNameNe(e.target.value)} placeholder="सीता" lang="ne" maxLength={20} />
        </label>
        <label className="block">
          <span className="mb-2 block text-h3 font-semibold">Name (English)</span>
          <input className={`${input} font-story-en`} value={nameEn} onChange={(e) => setNameEn(e.target.value)} placeholder="Sita" maxLength={20} />
        </label>
      </div>

      <Choice label="मन पर्ने जनावर · Favourite animal" options={ANIMALS} value={animal} onChange={setAnimal} />
      <Choice label="मन पर्ने खाना · Favourite food" options={FOODS} value={food} onChange={setFood} />
      <Choice label="कहाँ बस्छ? · Where they live" options={SETTINGS} value={setting} onChange={setSetting} />

      {error && <p className="mb-4 text-body text-omitted">{error}</p>}
      <button
        type="button"
        disabled={!ready || saving}
        onClick={submit}
        className="min-h-16 rounded-xl border-b-4 border-primary-hover bg-primary px-8 text-child-label font-bold text-on-primary transition-colors duration-150 hover:bg-primary-hover active:translate-y-1 active:border-b-0 disabled:border-ink-3 disabled:bg-ink-4"
      >
        {saving ? '…' : 'सुरु गरौँ · Start'}
      </button>
    </main>
  )
}
