/**
 * Sources whose feed keeps failing - dropped from the deck so dead cards never
 * show (the mobile mirror of the web `markFailed` / NewsColumnContext filter).
 * In-memory only: session-scoped, like web's component state; a relaunch
 * retries every source.
 *
 * Strikes, not one shot: the feed polls every 60s, so a single offline blip or
 * upstream 502 would otherwise remove a card for the rest of the session with
 * no way back - and if it was the card being read, the deck shifted underneath
 * the reader.
 */

/** Consecutive failures before a source is treated as dead. */
export const FAILURES_BEFORE_DROP = 3

// Dropping unmounts the card, which stops its polling - so without a timer a
// source that recovers stays gone until the app is relaunched. Give it another
// go; if it's still dead it simply drops again.
const RETRY_DROPPED_AFTER_MS = 10 * 60_000

const strikes = new Map<string, number>()
const retryTimers = new Map<string, ReturnType<typeof setTimeout>>()
let failed: readonly string[] = []

const listeners = new Set<() => void>()
const emit = () => {
  for (const listener of listeners) listener()
}

export const subscribeFailed = (listener: () => void): (() => void) => {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

export const getFailedSnapshot = (): readonly string[] => failed

/** Record a failed poll. Drops the source once it reaches the strike limit. */
export const markFailed = (id: string): void => {
  if (failed.includes(id)) return
  const count = (strikes.get(id) ?? 0) + 1
  strikes.set(id, count)
  if (count < FAILURES_BEFORE_DROP) return
  failed = [...failed, id]
  emit()
  const timer = setTimeout(() => {
    retryTimers.delete(id)
    markLoaded(id)
  }, RETRY_DROPPED_AFTER_MS)
  retryTimers.set(id, timer)
}

/** Record a poll that returned headlines, clearing any accumulated strikes. */
export const markLoaded = (id: string): void => {
  const timer = retryTimers.get(id)
  if (timer) {
    clearTimeout(timer)
    retryTimers.delete(id)
  }
  if (strikes.delete(id) && failed.includes(id)) {
    failed = failed.filter((x) => x !== id)
    emit()
  }
}
