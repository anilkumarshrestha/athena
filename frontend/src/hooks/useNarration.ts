import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api'

// "Read to me": play the story sentence by sentence and report which word is being spoken,
// from word timings computed on the server. Drives the same highlight as live follow-along.

type Sentence = { audio_url: string; words: { index: number; start: number; end: number }[] }

export function useNarration(storyId: string | undefined) {
  const [playing, setPlaying] = useState(false)
  const [word, setWord] = useState<number | null>(null)
  const [spoken, setSpoken] = useState<Set<number>>(new Set())
  const audio = useRef<HTMLAudioElement | null>(null)
  const raf = useRef(0)
  const token = useRef(0)

  const stop = useCallback(() => {
    token.current++
    audio.current?.pause()
    cancelAnimationFrame(raf.current)
    setPlaying(false)
    setWord(null)
  }, [])

  const play = useCallback(async () => {
    if (!storyId) return
    stop()
    const my = ++token.current
    setPlaying(true)
    setSpoken(new Set())
    let sentences: Sentence[]
    try {
      sentences = (await api.narration(storyId)) as Sentence[]
    } catch {
      setPlaying(false)
      return
    }
    for (const s of sentences) {
      if (my !== token.current) return
      const a = new Audio(s.audio_url)
      audio.current = a
      const tick = () => {
        const t = a.currentTime
        const w = s.words.find((x) => t >= x.start && t < x.end + 0.15) ?? null
        if (w) {
          setWord(w.index)
          setSpoken((prev) => (prev.has(w.index) ? prev : new Set(prev).add(w.index)))
        }
        raf.current = requestAnimationFrame(tick)
      }
      await new Promise<void>((resolve) => {
        a.onended = () => resolve()
        a.onerror = () => resolve()
        a.play().then(() => (raf.current = requestAnimationFrame(tick))).catch(() => resolve())
      })
      cancelAnimationFrame(raf.current)
      setSpoken((prev) => new Set([...prev, ...s.words.map((x) => x.index)]))
      await new Promise((r) => setTimeout(r, 350)) // breath between sentences
    }
    if (my === token.current) {
      setPlaying(false)
      setWord(null)
    }
  }, [storyId, stop])

  useEffect(() => stop, [stop]) // stop when leaving the story
  return { playing, word, spoken, play, stop }
}
