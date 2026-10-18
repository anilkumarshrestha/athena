import { useEffect, useRef, useState } from 'react'
import { api } from '../api'

// The official "Sign in with Google" button (Google Identity Services, loaded on demand).
// The server verifies the token and links the account to this family (athena/api.py).

type Gis = {
  accounts: { id: { initialize: (o: object) => void; renderButton: (el: HTMLElement, o: object) => void } }
}
const GIS_SRC = 'https://accounts.google.com/gsi/client'

function loadGis(): Promise<Gis> {
  const w = window as unknown as { google?: Gis }
  if (w.google?.accounts) return Promise.resolve(w.google)
  return new Promise((resolve, reject) => {
    const el = document.createElement('script')
    el.src = GIS_SRC
    el.async = true
    el.onload = () => (w.google ? resolve(w.google) : reject(new Error('no gis')))
    el.onerror = reject
    document.head.appendChild(el)
  })
}

export function GoogleButton({ clientId, onSignedIn }: { clientId: string; onSignedIn: (email: string | null) => void }) {
  const box = useRef<HTMLDivElement | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadGis()
      .then((g) => {
        g.accounts.id.initialize({
          client_id: clientId,
          callback: (r: { credential: string }) =>
            api
              .googleSignIn(r.credential)
              .then((f) => onSignedIn(f.email ?? null))
              .catch(() => setError('Sign-in did not work. Please try again.')),
        })
        if (box.current) g.accounts.id.renderButton(box.current, { theme: 'outline', size: 'large', text: 'signin_with', shape: 'pill' })
      })
      .catch(() => setError('Google sign-in could not load.'))
  }, [clientId, onSignedIn])

  return (
    <div>
      <div ref={box} className="flex justify-center" />
      {error && <p className="m-0 mt-2 text-small text-omitted">{error}</p>}
    </div>
  )
}
