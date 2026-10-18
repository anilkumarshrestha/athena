// DESIGN.md §6.6: the card check's progress as a river crossing. The child's animal hops
// from stone to stone (one per round) and reaches the far bank at the end.
// Stone states differ by shape and colour: passed = green with ✓, current = larger sun
// stone, ahead = white with an outline.

const W = 640
const H = 200
const BANK = 92 // width of each bank
const WATER_Y = 70
const WATER_H = 92
const STONE_Y = WATER_Y + WATER_H / 2 + 6

export function RiverCrossing({
  stones,
  current,
  done = false,
  pictureUrl,
  label,
}: {
  stones: number
  current: number // index of the stone the animal is on
  done?: boolean // reached the far bank
  pictureUrl: string
  label: string
}) {
  const gap = (W - 2 * BANK) / (stones + 1)
  const stoneX = (i: number) => BANK + gap * (i + 1)
  const animalX = done ? W - BANK / 2 : current < 0 ? BANK / 2 : stoneX(current)
  const animalY = done || current < 0 ? WATER_Y - 6 : STONE_Y - 40

  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={label} className="mb-6 block h-auto w-full">
      {/* sky band behind */}
      <rect x="0" y="0" width={W} height={H} rx="24" fill="var(--color-sky-soft)" />
      {/* water */}
      <rect x={BANK - 10} y={WATER_Y} width={W - 2 * BANK + 20} height={WATER_H} fill="var(--color-sky)" opacity="0.35" />
      {[0, 1, 2].map((k) => {
        const y = WATER_Y + 18 + k * 26
        const d = Array.from({ length: 9 }, (_, i) => {
          const x = BANK + 8 + i * ((W - 2 * BANK - 16) / 8)
          return `${i === 0 ? 'M' : 'Q'}${i === 0 ? `${x} ${y}` : `${x - 18} ${y + (i % 2 ? -6 : 6)} ${x} ${y}`}`
        }).join(' ')
        return <path key={k} d={d} fill="none" stroke="var(--color-sky-edge)" strokeWidth="2.5" strokeLinecap="round" opacity="0.6" />
      })}
      {/* banks */}
      <path d={`M0 ${WATER_Y - 18} H${BANK} Q${BANK + 14} ${H / 2} ${BANK} ${H} H0 Z`} fill="var(--color-leaf-soft)" />
      <path d={`M${W} ${WATER_Y - 18} H${W - BANK} Q${W - BANK - 14} ${H / 2} ${W - BANK} ${H} H${W} Z`} fill="var(--color-leaf-soft)" />
      {[18, 52, W - 70, W - 30].map((x) => (
        <path key={x} d={`M${x} ${H - 26} l4 -14 l4 14 m-2 0 l6 -18 l3 18`} fill="none" stroke="var(--color-leaf)" strokeWidth="3" strokeLinecap="round" />
      ))}
      {/* goal flag on the far bank */}
      <line x1={W - 34} y1={WATER_Y - 18} x2={W - 34} y2={WATER_Y - 66} stroke="var(--color-ink-3)" strokeWidth="3" strokeLinecap="round" />
      <path d={`M${W - 34} ${WATER_Y - 66} l30 9 l-30 9 Z`} fill="var(--color-sun)" stroke="var(--color-sun-edge)" strokeWidth="2" strokeLinejoin="round" />

      {/* stepping stones */}
      {Array.from({ length: stones }, (_, i) => {
        const passed = done || i < current
        const here = !done && i === current
        const rx = here ? 30 : 25
        return (
          <g key={i}>
            <ellipse cx={stoneX(i)} cy={STONE_Y + 4} rx={rx} ry={rx * 0.42} fill="var(--color-ink)" opacity="0.12" />
            <ellipse
              cx={stoneX(i)}
              cy={STONE_Y}
              rx={rx}
              ry={rx * 0.42}
              fill={passed ? 'var(--color-leaf)' : here ? 'var(--color-sun)' : 'var(--color-card)'}
              stroke={passed ? 'var(--color-leaf-edge)' : here ? 'var(--color-sun-edge)' : 'var(--color-line-strong)'}
              strokeWidth="3"
            />
            {passed && (
              <path d={`M${stoneX(i) - 8} ${STONE_Y} l5 5 l10 -10`} fill="none" stroke="var(--color-on-primary)" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round" />
            )}
          </g>
        )
      })}

      {/* the animal: hops with a short ease-out move (reduced motion: just appears) */}
      <g style={{ transform: `translate(${animalX}px, ${animalY}px)`, transition: 'transform 400ms var(--ease-out)' }}>
        <circle r="34" fill="var(--color-card)" stroke="var(--color-on-primary)" strokeWidth="4" />
        <clipPath id="animal-clip">
          <circle r="30" />
        </clipPath>
        <image href={pictureUrl} x="-30" y="-30" width="60" height="60" clipPath="url(#animal-clip)" preserveAspectRatio="xMidYMid slice" />
        <circle r="31" fill="none" stroke="var(--color-line-strong)" strokeWidth="2" />
      </g>
    </svg>
  )
}
