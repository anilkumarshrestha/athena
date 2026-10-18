// Interface language for labels around the reading (not the stories, letters or anything the
// child reads). English by default: most visitors and judges read English. In Nepali the
// labels stay bilingual ("यो हप्ता · This week"). Chosen on the landing page or the learner
// screen, remembered in this browser (per-viewer convenience only).

export type UiLang = 'en' | 'ne'
const KEY = 'athena.uiLang'
const EVENT = 'athena-ui-lang'

export function uiLang(): UiLang {
  try {
    return localStorage.getItem(KEY) === 'ne' ? 'ne' : 'en'
  } catch {
    return 'en'
  }
}

export function setUiLang(l: UiLang): void {
  try {
    localStorage.setItem(KEY, l)
  } catch {
    /* not remembered: still switches for this page */
  }
  dispatchEvent(new CustomEvent(EVENT, { detail: l }))
}

export function onUiLang(fn: (l: UiLang) => void): () => void {
  const h = (e: Event) => fn((e as CustomEvent<UiLang>).detail)
  addEventListener(EVENT, h)
  return () => removeEventListener(EVENT, h)
}

/** A bilingual label: English only in the English interface, "ने · EN" in the Nepali one. */
export function bi(ne: string, en: string): string {
  return uiLang() === 'en' ? en : `${ne} · ${en}`
}
