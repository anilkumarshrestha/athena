import { useEffect, useState } from 'react'
import { api, type Language } from './api'
import { ParentGate } from './components/ParentGate'
import { AddLearner } from './screens/AddLearner'
import { DiagnosticScreen } from './screens/DiagnosticScreen'
import { LearnerPick } from './screens/LearnerPick'
import { MasteryScreen } from './screens/MasteryScreen'
import { MathsScreen } from './screens/MathsScreen'
import { ParentScreen } from './screens/ParentScreen'
import { StoryReview } from './screens/StoryReview'
import { StoryScreen } from './screens/StoryScreen'
import { Landing } from './screens/Landing'
import { Styleguide } from './screens/Styleguide'
import { TeachScreen } from './screens/TeachScreen'
import { go, interceptLinks } from './nav'

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
  | { name: 'landing' }

// Routes (clean paths, nav.ts): /  /app  /new  /check/<learner>/<ne|en>  /styleguide  /mastery/<learner>
//   /parent/<learner>[/story/<id>]  /read/<learner>/<ne|en>  /maths/<learner>/<ne|en>  /teach/<learner>/<ne|en>
function parse(path: string): Route {
  const p = path.replace(/\/+$/, '') || '/'
  if (p === '/') return { name: 'landing' }
  if (p === '/app') return { name: 'pick' }
  if (p === '/styleguide') return { name: 'styleguide' }
  if (p === '/new') return { name: 'new' }
  const ck = p.match(/^\/check\/([\w-]+)\/(ne|en)$/)
  if (ck) return { name: 'check', learnerId: ck[1], lang: ck[2] as Language }
  const mm = p.match(/^\/mastery\/([\w-]+)$/)
  if (mm) return { name: 'mastery', learnerId: mm[1] }
  const rv = p.match(/^\/parent\/([\w-]+)\/story\/([\w-]+)$/)
  if (rv) return { name: 'review', learnerId: rv[1], storyId: rv[2] }
  const pm = p.match(/^\/parent\/([\w-]+)$/)
  if (pm) return { name: 'parent', learnerId: pm[1] }
  const mt = p.match(/^\/maths\/([\w-]+)\/(ne|en)$/)
  if (mt) return { name: 'maths', learnerId: mt[1], lang: mt[2] as Language }
  const tc = p.match(/^\/teach\/([\w-]+)\/(ne|en)$/)
  if (tc) return { name: 'teach', learnerId: tc[1], lang: tc[2] as Language }
  const m = p.match(/^\/read\/([\w-]+)\/(ne|en)$/)
  return m ? { name: 'story', learnerId: m[1], lang: m[2] as Language } : { name: 'landing' }
}

// Old links (/#/parent/x) still work: moved to the clean path once, before the first render.
if (location.hash.startsWith('#/')) history.replaceState(null, '', location.hash.slice(1))

export default function App() {
  const [route, setRoute] = useState<Route>(() => parse(location.pathname))

  useEffect(() => {
    const onNav = () => {
      setRoute(parse(location.pathname))
      scrollTo(0, 0)
    }
    addEventListener('popstate', onNav)
    const stop = interceptLinks()
    return () => {
      removeEventListener('popstate', onNav)
      stop()
    }
  }, [])

  if (route.name === 'landing') return <Landing />
  if (route.name === 'styleguide') return <Styleguide />
  if (route.name === 'new')
    return (
      <AddLearner
        onDone={(id, langs) => go(`/check/${id}/${langs === 'en' ? 'en' : 'ne'}`)}
        onBack={() => go('/app')}
      />
    )
  if (route.name === 'check')
    return (
      <DiagnosticScreen
        key={`${route.learnerId}/${route.lang}`}
        learnerId={route.learnerId}
        lang={route.lang}
        // Nepali first, then English (if the child learns both), then the learner list
        onDone={() =>
          api
            .learner(route.learnerId)
            .then((l) => go(route.lang === 'ne' && (l.profile.languages ?? 'both') !== 'ne' ? `/check/${route.learnerId}/en` : '/app'))
            .catch(() => go('/app'))
        }
      />
    )
  if (route.name === 'review')
    return <ParentGate onBack={() => go('/app')}><StoryReview learnerId={route.learnerId} storyId={route.storyId} onBack={() => go(`/parent/${route.learnerId}`)} /></ParentGate>
  const home = () => go('/app')
  if (route.name === 'parent')
    return <ParentGate onBack={home}><ParentScreen learnerId={route.learnerId} onBack={home} /></ParentGate>
  if (route.name === 'mastery')
    return <ParentGate onBack={home}><MasteryScreen learnerId={route.learnerId} onBack={home} /></ParentGate>
  if (route.name === 'teach')
    return <TeachScreen key={`${route.learnerId}/${route.lang}`} learnerId={route.learnerId} lang={route.lang} onBack={() => go('/app')} />
  if (route.name === 'maths')
    return <MathsScreen key={`${route.learnerId}/${route.lang}`} learnerId={route.learnerId} lang={route.lang} onBack={() => go('/app')} />
  if (route.name === 'story') {
    return (
      <StoryScreen
        key={`${route.learnerId}/${route.lang}`}
        learnerId={route.learnerId}
        lang={route.lang}
        onBack={() => go('/app')}
      />
    )
  }
  return <LearnerPick onPick={(learnerId, lang) => go(`/read/${learnerId}/${lang}`)} />
}
