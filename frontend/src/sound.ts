// Sound effects (DESIGN.md §4 Sound), synthesised with the Web Audio API: no files.
// Short, soft, warm; never a "wrong" sound; silent while the mic records (the caller
// must not play during recording); muted by a parent toggle remembered on this device.

let ctx: AudioContext | null = null
const KEY = 'athena.sound'

function muted(): boolean {
  try {
    return localStorage.getItem(KEY) === 'off'
  } catch {
    return false
  }
}

export function soundOn(): boolean {
  return !muted()
}

export function setSoundOn(on: boolean): void {
  try {
    localStorage.setItem(KEY, on ? 'on' : 'off')
  } catch {
    /* private mode: stays on for this visit */
  }
}

function ac(): AudioContext | null {
  if (muted()) return null
  try {
    ctx ??= new AudioContext()
    if (ctx.state === 'suspended') ctx.resume().catch(() => {})
    return ctx
  } catch {
    return null
  }
}

// One soft note: sine (or triangle) with a quick attack and gentle decay.
function note(freq: number, start: number, dur: number, vol = 0.12, type: OscillatorType = 'sine', glideTo?: number) {
  const a = ac()
  if (!a) return
  const t = a.currentTime + start
  const osc = a.createOscillator()
  const gain = a.createGain()
  osc.type = type
  osc.frequency.setValueAtTime(freq, t)
  if (glideTo) osc.frequency.exponentialRampToValueAtTime(glideTo, t + dur)
  gain.gain.setValueAtTime(0.0001, t)
  gain.gain.exponentialRampToValueAtTime(vol, t + 0.012)
  gain.gain.exponentialRampToValueAtTime(0.0001, t + dur)
  osc.connect(gain).connect(a.destination)
  osc.start(t)
  osc.stop(t + dur + 0.02)
}

export const sfx = {
  /** tap a word, tile, letter card */
  pop: () => note(660, 0, 0.09, 0.1, 'sine', 990),
  /** record start / stop */
  click: () => note(1200, 0, 0.04, 0.06, 'triangle'),
  /** reading scored, retry correct: warm two notes (C6, E6) */
  chime: () => {
    note(1046.5, 0, 0.35, 0.09)
    note(1318.5, 0.09, 0.4, 0.08)
  },
  /** new letters unlocked: small rising sparkle */
  sparkle: () => [1318.5, 1568, 2093].forEach((f, i) => note(f, i * 0.06, 0.22, 0.06)),
  /** animal hops to the next stone: water plop */
  plop: () => note(520, 0, 0.16, 0.12, 'sine', 180),
  /** river crossed: short happy tune (C5 E5 G5 C6) */
  tada: () => [523.25, 659.25, 783.99, 1046.5].forEach((f, i) => note(f, i * 0.11, i === 3 ? 0.45 : 0.18, 0.1, 'triangle')),
}
