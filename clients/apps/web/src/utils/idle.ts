/** Run *work* when the main thread is idle (or after *timeout* ms, whichever
 * comes first), returning a cancel function. Keeps analytics and prefetches
 * out of the wall's critical first paint. */
export const runWhenIdle = (work: () => void, timeout = 5000): (() => void) => {
  if (typeof window === 'undefined') return () => {}
  if (typeof window.requestIdleCallback === 'function') {
    const id = window.requestIdleCallback(work, { timeout })
    return () => window.cancelIdleCallback(id)
  }
  // Older Safari: no requestIdleCallback — a short timeout approximates it.
  const id = window.setTimeout(work, timeout)
  return () => window.clearTimeout(id)
}
