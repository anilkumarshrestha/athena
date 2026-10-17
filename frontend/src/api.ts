import type { components } from './api-types'

export type Learner = components['schemas']['LearnerOut']
export type Story = components['schemas']['StoryOut']
export type Attempt = components['schemas']['AttemptLog']
export type Language = Story['language']
export type DisplayWord = components['schemas']['DisplayWord']
export type ReadResult = components['schemas']['ReadOut']
export type CloseResult = components['schemas']['CloseOut']

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    // FastAPI validation errors come as a list: show the first message
    const detail = Array.isArray(body.detail) ? body.detail[0]?.msg : body.detail
    throw new Error(detail ?? `HTTP ${res.status}`)
  }
  return res.json()
}

export const api = {
  learners: () => fetch('/api/learners').then(json<Learner[]>),
  learner: (id: string) => fetch(`/api/learners/${id}`).then(json<Learner>),
  diagnostic: (learnerId: string, lang: Language) =>
    fetch(`/api/learners/${learnerId}/diagnostic/${lang}`).then(json<components['schemas']['DiagnosticOut']>),
  placement: (learnerId: string, language: Language, responses: Record<string, boolean>) =>
    fetch(`/api/learners/${learnerId}/placement`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ language, responses }),
    }).then(json<components['schemas']['PlacementOut']>),
  createLearner: (body: components['schemas']['LearnerCreate']) =>
    fetch('/api/learners', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(body),
    }).then(json<Learner>),
  startSession: (learner_id: string, language: Language) =>
    fetch('/api/session/start', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ learner_id, language }),
    }).then(json<Story>),
  story: (id: string) => fetch(`/api/stories/${id}`).then(json<Story>),
  closeSession: (story_id: string) =>
    fetch('/api/session/close', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ story_id }),
    }).then(json<CloseResult>),
  // Audio is scored in memory on the server and never stored.
  read: (storyId: string, audio: Blob, durationS: number) => {
    const form = new FormData()
    form.append('story_id', storyId)
    form.append('duration_s', String(Math.max(0.5, durationS)))
    form.append('audio', audio, audio.type.includes('mp4') ? 'read.mp4' : 'read.webm')
    return fetch('/api/session/read', { method: 'POST', body: form }).then(json<ReadResult>)
  },
}
