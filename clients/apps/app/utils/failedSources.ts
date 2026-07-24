/**
 * Sources whose feed failed to load this session — dropped from the deck so
 * dead cards never show (the mobile mirror of the web `markFailed` /
 * NewsColumnContext failed-source filter). In-memory only: session-scoped, like
 * web's component state; a relaunch retries every source.
 */

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

/** Mark a source's feed as failed (idempotent). */
export const markFailed = (id: string): void => {
  if (failed.includes(id)) return
  failed = [...failed, id]
  emit()
}
