import { useEffect, useState } from 'react'
import type { Language } from './api'
import { LearnerPick } from './screens/LearnerPick'
import { StoryScreen } from './screens/StoryScreen'

type Route = { name: 'pick' } | { name: 'story'; learnerId: string; lang: Language }

// Hash routes: #/  and  #/read/<learner>/<ne|en>
function parse(hash: string): Route {
  const m = hash.match(/^#\/read\/([\w-]+)\/(ne|en)$/)
  return m ? { name: 'story', learnerId: m[1], lang: m[2] as Language } : { name: 'pick' }
}

export default function App() {
  const [route, setRoute] = useState<Route>(() => parse(location.hash))

  useEffect(() => {
    const onHash = () => setRoute(parse(location.hash))
    addEventListener('hashchange', onHash)
    return () => removeEventListener('hashchange', onHash)
  }, [])

  if (route.name === 'story') {
    return (
      <StoryScreen
        key={`${route.learnerId}/${route.lang}`}
        learnerId={route.learnerId}
        lang={route.lang}
        onBack={() => (location.hash = '#/')}
      />
    )
  }
  return <LearnerPick onPick={(learnerId, lang) => (location.hash = `#/read/${learnerId}/${lang}`)} />
}
