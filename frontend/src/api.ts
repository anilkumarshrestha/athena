import type { components } from './api-types'

export type Learner = components['schemas']['LearnerOut']
export type Story = components['schemas']['StoryOut']
export type Attempt = components['schemas']['AttemptLog']
export type Language = Story['language']

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail ?? `HTTP ${res.status}`)
  }
  return res.json()
}

export const api = {
  learners: () => fetch('/api/learners').then(json<Learner[]>),
  learner: (id: string) => fetch(`/api/learners/${id}`).then(json<Learner>),
  startSession: (learner_id: string, language: Language) =>
    fetch('/api/session/start', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ learner_id, language }),
    }).then(json<Story>),
  story: (id: string) => fetch(`/api/stories/${id}`).then(json<Story>),
}
