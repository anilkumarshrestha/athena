import { useCallback, useRef, useState } from 'react'

export type RecorderState = 'idle' | 'recording' | 'error'

// WebM/Opus where supported (Chrome, Firefox); MP4/AAC on Safari.
const MIME_TYPES = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4']

export function useRecorder() {
  const [state, setState] = useState<RecorderState>('idle')
  const [error, setError] = useState<string | null>(null)
  const rec = useRef<MediaRecorder | null>(null)
  const chunks = useRef<Blob[]>([])
  const startedAt = useRef(0)

  const start = useCallback(async () => {
    setError(null)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mimeType = MIME_TYPES.find((t) => MediaRecorder.isTypeSupported(t))
      const r = new MediaRecorder(stream, mimeType ? { mimeType } : undefined)
      chunks.current = []
      r.ondataavailable = (e) => e.data.size && chunks.current.push(e.data)
      r.start()
      rec.current = r
      startedAt.current = performance.now()
      setState('recording')
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setState('error')
    }
  }, [])

  // Resolves with the recording; the microphone is released immediately.
  const stop = useCallback(
    () =>
      new Promise<{ blob: Blob; durationS: number }>((resolve, reject) => {
        const r = rec.current
        if (!r) return reject(new Error('not recording'))
        r.onstop = () => {
          r.stream.getTracks().forEach((t) => t.stop())
          rec.current = null
          setState('idle')
          resolve({
            blob: new Blob(chunks.current, { type: r.mimeType || 'audio/webm' }),
            durationS: (performance.now() - startedAt.current) / 1000,
          })
        }
        r.stop()
      }),
    [],
  )

  return { state, error, start, stop }
}
