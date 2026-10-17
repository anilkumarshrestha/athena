// DESIGN.md §6.5: quiet 3-dot loader. No spinner, no shimmer.
export function DotLoader({ label }: { label?: string }) {
  return (
    <span role="status" aria-label={label ?? 'Loading'} className="inline-flex gap-2">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="size-2.5 rounded-full bg-ink-3"
          style={{ animation: `dot-fade 1.2s ${i * 0.16}s infinite ease-in-out` }}
        />
      ))}
    </span>
  )
}
