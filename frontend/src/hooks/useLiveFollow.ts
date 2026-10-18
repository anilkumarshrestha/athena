import { useCallback, useRef, useState } from 'react'

// Live follow-along: stream the mic as 16 kHz PCM over a WebSocket; the server answers
// with the story words heard so far and the next word to read. A visual guide only:
// the reading is still scored from the full recording. Any failure just turns it off.

const WORKLET = `
class Pcm16 extends AudioWorkletProcessor {
  constructor() { super(); this.buf = []; this.n = 0 }
  process(inputs) {
    const ch = inputs[0] && inputs[0][0]
    if (ch) {
      const out = new Int16Array(ch.length)
      for (let i = 0; i < ch.length; i++) out[i] = Math.max(-1, Math.min(1, ch[i])) * 0x7fff
      this.buf.push(out); this.n += out.length
      if (this.n >= 800) {                // ~50 ms at 16 kHz: the highlight keeps up
        const all = new Int16Array(this.n); let o = 0
        for (const b of this.buf) { all.set(b, o); o += b.length }
        this.port.postMessage(all.buffer, [all.buffer]); this.buf = []; this.n = 0
      }
    }
    return true
  }
}
registerProcessor('pcm16', Pcm16)`

export function useLiveFollow(storyId: string | undefined) {
  const [heard, setHeard] = useState<Set<number>>(new Set())
  const [next, setNext] = useState<number | null>(null)
  const ws = useRef<WebSocket | null>(null)
  const ctx = useRef<AudioContext | null>(null)
  const stopAsked = useRef(false)

  const start = useCallback(
    async (stream: MediaStream) => {
      if (!storyId) return
      setHeard(new Set())
      setNext(0)
      try {
        const proto = location.protocol === 'https:' ? 'wss' : 'ws'
        const sock = new WebSocket(`${proto}://${location.host}/api/stories/${storyId}/live`)
        sock.binaryType = 'arraybuffer'
        sock.onmessage = (e) => {
          const m = JSON.parse(e.data)
          if (m.done) return
          setHeard(new Set<number>(m.heard))
          setNext(m.next)
        }
        sock.onerror = () => setNext(null)
        // The mic starts before the socket is open: hold those first chunks instead of
        // dropping them (the first word used to be lost or late), send them on open.
        const pending: ArrayBuffer[] = []
        sock.onopen = () => {
          for (const b of pending.splice(0)) sock.send(b)
          if (stopAsked.current) sock.send('stop')
        }
        stopAsked.current = false
        ws.current = sock

        // The browser resamples the mic to 16 kHz for this context (Chrome, Safari, Firefox).
        const ac = new AudioContext({ sampleRate: 16000 })
        ctx.current = ac
        const url = URL.createObjectURL(new Blob([WORKLET], { type: 'application/javascript' }))
        await ac.audioWorklet.addModule(url)
        URL.revokeObjectURL(url)
        const node = new AudioWorkletNode(ac, 'pcm16')
        node.port.onmessage = (e) => {
          if (sock.readyState === WebSocket.OPEN) sock.send(e.data)
          else if (sock.readyState === WebSocket.CONNECTING && pending.length < 200) pending.push(e.data) // ≤10 s
        }
        ac.createMediaStreamSource(stream).connect(node)
      } catch {
        setNext(null) // live view unavailable: recording and scoring still work
      }
    },
    [storyId],
  )

  const stop = useCallback(() => {
    const sock = ws.current
    if (sock?.readyState === WebSocket.OPEN) sock.send('stop')
    else stopAsked.current = true // still connecting: onopen sends the held audio, then stop
    setTimeout(() => sock?.close(), 3000) // let the last words arrive
    ws.current = null
    ctx.current?.close().catch(() => {})
    ctx.current = null
    setNext(null)
  }, [])

  return { heard, next, start, stop }
}
