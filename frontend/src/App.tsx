import { useEffect, useState } from 'react'
import type { Language } from './api'
import { LearnerPick } from './screens/LearnerPick'
import { MasteryScreen } from './screens/MasteryScreen'
import { StoryScreen } from './screens/StoryScreen'
import { Styleguide } from './screens/Styleguide'

type Route =
  | { name: 'pick' }
  | { name: 'styleguide' }
  | { name: 'mastery'; learnerId: string }
  | { name: 'story'; learnerId: string; lang: Language }

// Hash routes: #/  #/styleguide  #/mastery/<learner>  #/read/<learner>/<ne|en>
function parse(hash: string): Route {
  if (hash === '#/styleguide') return { name: 'styleguide' }
  const mm = hash.match(/^#\/mastery\/([\w-]+)$/)
  if (mm) return { name: 'mastery', learnerId: mm[1] }
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

  if (route.name === 'styleguide') return <Styleguide />
  if (route.name === 'mastery') return <MasteryScreen learnerId={route.learnerId} onBack={() => (location.hash = '#/')} />
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
