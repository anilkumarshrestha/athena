// Clean paths (/app, /parent/<id>) with the History API. The server returns the app for any
// non-/api path (athena/api.py spa), so links and refreshes work; Back works as usual.

export function go(path: string, replace = false): void {
  const state = { inApp: true } // the page before this one is ours: "back" can go there
  if (replace) history.replaceState(history.state, '', path)
  else history.pushState(state, '', path)
  dispatchEvent(new PopStateEvent('popstate'))
}

/** Back to the previous page if it is ours (not another site), else to a fallback page. */
export function back(fallback: string): void {
  if ((history.state as { inApp?: boolean } | null)?.inApp) history.back()
  else go(fallback)
}

// Plain <a href="/..."> links inside the app navigate without a page load.
export function interceptLinks(): () => void {
  const onClick = (e: MouseEvent) => {
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return
    const a = (e.target as Element | null)?.closest?.('a')
    const href = a?.getAttribute('href')
    if (!a || !href || !href.startsWith('/') || href.startsWith('/api/') || a.target) return
    e.preventDefault()
    go(href)
  }
  document.addEventListener('click', onClick)
  return () => document.removeEventListener('click', onClick)
}
