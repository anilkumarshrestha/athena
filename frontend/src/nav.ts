// Clean paths (/app, /parent/<id>) with the History API. The server returns the app for any
// non-/api path (athena/api.py spa), so links and refreshes work; Back works as usual.

export function go(path: string, replace = false): void {
  if (replace) history.replaceState(null, '', path)
  else history.pushState(null, '', path)
  dispatchEvent(new PopStateEvent('popstate'))
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
