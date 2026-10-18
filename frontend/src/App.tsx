import { useEffect, useState } from 'react'
import type { Language } from './api'
import { AddLearner } from './screens/AddLearner'
import { DiagnosticScreen } from './screens/DiagnosticScreen'
import { LearnerPick } from './screens/LearnerPick'
import { MasteryScreen } from './screens/MasteryScreen'
import { MathsScreen } from './screens/MathsScreen'
import { ParentScreen } from './screens/ParentScreen'
import { StoryReview } from './screens/StoryReview'
import { StoryScreen } from './screens/StoryScreen'
import { Styleguide } from './screens/Styleguide'
import { TeachScreen } from './screens/TeachScreen'

type Route =
  | { name: 'pick' }
  | { name: 'styleguide' }
  | { name: 'new' }
  | { name: 'check'; learnerId: string; lang: Language }
  | { name: 'mastery'; learnerId: string }
  | { name: 'parent'; learnerId: string }
  | { name: 'review'; learnerId: string; storyId: string }
  | { name: 'story'; learnerId: string; lang: Language }
  | { name: 'maths'; learnerId: string; lang: Language }
  | { name: 'teach'; learnerId: string; lang: Language }

// Hash routes: #/  #/new  #/check/<learner>/<ne|en>  #/styleguide  #/mastery/<learner>  #/read/<learner>/<ne|en>
function parse(hash: string): Route {
  if (hash === '#/styleguide') return { name: 'styleguide' }
  if (hash === '#/new') return { name: 'new' }
  const ck = hash.match(/^#\/check\/([\w-]+)\/(ne|en)$/)
  if (ck) return { name: 'check', learnerId: ck[1], lang: ck[2] as Language }
  const mm = hash.match(/^#\/mastery\/([\w-]+)$/)
  if (mm) return { name: 'mastery', learnerId: mm[1] }
  const rv = hash.match(/^#\/parent\/([\w-]+)\/story\/([\w-]+)$/)
  if (rv) return { name: 'review', learnerId: rv[1], storyId: rv[2] }
  const pm = hash.match(/^#\/parent\/([\w-]+)$/)
  if (pm) return { name: 'parent', learnerId: pm[1] }
  const mt = hash.match(/^#\/maths\/([\w-]+)\/(ne|en)$/)
  if (mt) return { name: 'maths', learnerId: mt[1], lang: mt[2] as Language }
  const tc = hash.match(/^#\/teach\/([\w-]+)\/(ne|en)$/)
  if (tc) return { name: 'teach', learnerId: tc[1], lang: tc[2] as Language }
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
  if (route.name === 'new')
    return <AddLearner onDone={(id) => (location.hash = `#/check/${id}/ne`)} onBack={() => (location.hash = '#/')} />
  if (route.name === 'check')
    return (
      <DiagnosticScreen
        key={`${route.learnerId}/${route.lang}`}
        learnerId={route.learnerId}
        lang={route.lang}
        // Nepali first, then English, then the learner list
        onDone={() => (location.hash = route.lang === 'ne' ? `#/check/${route.learnerId}/en` : '#/')}
      />
    )
  if (route.name === 'review')
    return <StoryReview learnerId={route.learnerId} storyId={route.storyId} onBack={() => (location.hash = `#/parent/${route.learnerId}`)} />
  if (route.name === 'parent') return <ParentScreen learnerId={route.learnerId} onBack={() => (location.hash = '#/')} />
  if (route.name === 'mastery') return <MasteryScreen learnerId={route.learnerId} onBack={() => (location.hash = '#/')} />
  if (route.name === 'teach')
    return <TeachScreen key={`${route.learnerId}/${route.lang}`} learnerId={route.learnerId} lang={route.lang} onBack={() => (location.hash = '#/')} />
  if (route.name === 'maths')
    return <MathsScreen key={`${route.learnerId}/${route.lang}`} learnerId={route.learnerId} lang={route.lang} onBack={() => (location.hash = '#/')} />
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
