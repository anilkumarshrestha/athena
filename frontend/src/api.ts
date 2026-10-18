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
  deleteLearner: (id: string) =>
    fetch(`/api/learners/${id}`, { method: 'DELETE' }).then((r) => {
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
    }),
  wordHelp: (storyId: string, index: number) =>
    fetch(`/api/stories/${storyId}/words/${index}`).then(json<components['schemas']['WordHelpOut']>),
  letterAudioUrl: (lang: Language, unit: string) => `/api/letters/${lang}/${encodeURIComponent(unit)}/audio`,
  closeLetters: (learnerId: string, language: Language, results: Record<string, boolean>) =>
    fetch(`/api/learners/${learnerId}/letters/close`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ language, results }),
    }).then(json<CloseResult>),
  praiseUrl: (lang: Language, tier: 'great' | 'good' | 'try') => `/api/praise/${lang}/${tier}`,
  history: (id: string) => fetch(`/api/learners/${id}/stories`).then(json<components['schemas']['HistoryItemOut'][]>),
  historyStory: (id: string, storyId: string) =>
    fetch(`/api/learners/${id}/stories/${storyId}`).then(json<components['schemas']['HistoryStoryOut']>),
  dashboard: (id: string) => fetch(`/api/learners/${id}/dashboard`).then(json<components['schemas']['DashboardOut']>),
  activities: (id: string, lang: Language) =>
    fetch(`/api/learners/${id}/activities/${lang}`).then(json<components['schemas']['ActivitiesOut']>),
  setDailyMinutes: (id: string, daily_minutes: 0 | 10 | 15 | 20 | 30) =>
    fetch(`/api/learners/${id}/settings`, {
      method: 'PUT',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ daily_minutes }),
    }).then(json<Learner>),
  wordAudioUrl: (storyId: string, index: number) => `/api/stories/${storyId}/words/${index}/audio`,
  retryWord: (storyId: string, index: number, audio: Blob) => {
    const form = new FormData()
    form.append('audio', audio, audio.type.includes('mp4') ? 'word.mp4' : 'word.webm')
    return fetch(`/api/stories/${storyId}/words/${index}/read`, { method: 'POST', body: form }).then(
      json<components['schemas']['RetryOut']>,
    )
  },
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
