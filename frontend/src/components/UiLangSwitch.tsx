import { useEffect, useState } from 'react'
import { onUiLang, setUiLang, uiLang, type UiLang } from '../ui'

// English | नेपाली for the interface labels (stories are not affected). Pill inside a pill.
export function UiLangSwitch() {
  const [lang, setLang] = useState<UiLang>(uiLang)
  useEffect(() => onUiLang(setLang), [])
  return (
    <div role="group" aria-label="Language" className="flex rounded-full border border-line-strong bg-card p-1">
      {(['en', 'ne'] as const).map((l) => (
        <button key={l} type="button" aria-pressed={lang === l} onClick={() => setUiLang(l)}
          className={`min-h-9 rounded-full px-3 text-small ${l === 'ne' ? 'font-story-ne' : ''} ${lang === l ? 'bg-primary-soft font-semibold text-primary' : 'text-ink-2 hover:bg-paper-sunken'}`}>
          {l === 'en' ? 'English' : 'नेपाली'}
        </button>
      ))}
    </div>
  )
}
