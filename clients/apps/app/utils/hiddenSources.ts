import AsyncStorage from '@react-native-async-storage/async-storage'

/**
 * Device-local hidden sources — the mobile mirror of the web wall's
 * "Unfollow on a card removes it". Backed by AsyncStorage, exposed as an
 * external store for `useSyncExternalStore`: the snapshot is served from an
 * in-memory cache (AsyncStorage is async), hydrated at first use and
 * re-attempted on later subscribes until it succeeds.
 *
 * Durability model: mutations made before hydration completes are appended to
 * a separate PENDING key via read-modify-write (so they survive an immediate
 * app kill, never clobber the unread main list, and never clobber a previous
 * session's own unmerged pending deltas). On a successful hydration the
 * pending deltas are folded into the main list — this session's taps winning
 * over a previous session's — and the pending key is cleared only AFTER the
 * main list has been written successfully.
 */

const HIDDEN_KEY = 'news.hiddenSources'
const PENDING_KEY = 'news.hiddenSources.pending'

const EMPTY: readonly string[] = []

type PendingDeltas = { added: string[]; removed: string[] }

let hidden: readonly string[] = EMPTY
let hydrated = false
let hydrationInFlight = false
// This session's pre-hydration taps, newest state wins (an id is in at most
// one of the two sets).
const added = new Set<string>()
const removed = new Set<string>()
// Serializes pending-key read-modify-writes so successive taps can't race
// each other.
let pendingWriteChain: Promise<void> = Promise.resolve()

const listeners = new Set<() => void>()
const emit = () => {
  for (const listener of listeners) listener()
}

const parseList = (raw: string | null): string[] => {
  if (!raw) return []
  try {
    const parsed: unknown = JSON.parse(raw)
    return Array.isArray(parsed)
      ? parsed.filter((x): x is string => typeof x === 'string')
      : []
  } catch {
    return []
  }
}

const parsePending = (raw: string | null): PendingDeltas => {
  if (!raw) return { added: [], removed: [] }
  try {
    const parsed: unknown = JSON.parse(raw)
    const obj = (parsed ?? {}) as Partial<PendingDeltas>
    return {
      added: Array.isArray(obj.added)
        ? obj.added.filter((x): x is string => typeof x === 'string')
        : [],
      removed: Array.isArray(obj.removed)
        ? obj.removed.filter((x): x is string => typeof x === 'string')
        : [],
    }
  } catch {
    return { added: [], removed: [] }
  }
}

/** Fold a snapshot of session deltas over older pending deltas (session
 * wins). Takes the deltas as arguments — NOT the live sets — because the
 * chain step may execute after hydration has already cleared them. */
const mergePending = (
  disk: PendingDeltas,
  sessionAdded: readonly string[],
  sessionRemoved: readonly string[],
): PendingDeltas => {
  const mergedAdded = new Set(disk.added)
  const mergedRemoved = new Set(disk.removed)
  for (const id of sessionRemoved) {
    mergedAdded.delete(id)
    mergedRemoved.add(id)
  }
  for (const id of sessionAdded) {
    mergedRemoved.delete(id)
    mergedAdded.add(id)
  }
  return { added: [...mergedAdded], removed: [...mergedRemoved] }
}

/** Read-modify-write the pending key, serialized per session. The delta sets
 * are snapshotted at enqueue time so a hydration completing (and clearing
 * the live sets) between enqueue and execution can't drop the tap. */
const persistPending = () => {
  const snapshotAdded = [...added]
  const snapshotRemoved = [...removed]
  pendingWriteChain = pendingWriteChain
    .then(() => AsyncStorage.getItem(PENDING_KEY))
    .then((raw) =>
      AsyncStorage.setItem(
        PENDING_KEY,
        JSON.stringify(
          mergePending(parsePending(raw), snapshotAdded, snapshotRemoved),
        ),
      ),
    )
    .catch(() => {
      // storage unavailable — memory still serves this session
    })
}

/** Delete the pending key, sequenced behind any queued pending writes so a
 * still-in-flight tap RMW can't recreate the file after its removal. */
const clearPendingSequenced = () => {
  pendingWriteChain = pendingWriteChain
    .then(() => AsyncStorage.removeItem(PENDING_KEY))
    .catch(() => {})
}

// True while a pending key that hydration could NOT read may still hold a
// previous session's unmerged deltas. Those deltas must never be deleted
// blind — persistMain instead tries to recover and fold them in.
let unmergedPendingOnDisk = false
// Ids the user has explicitly touched after hydration this session. A newer
// user action always beats a recovered older delta for the same id.
const touchedSinceHydration = new Set<string>()

/** Try to fold a previously-unreadable pending key into the current list:
 * apply its deltas (except ids the user has since touched), persist the
 * result, and only then delete the key. If it is still unreadable, leave it
 * for the next launch. */
const recoverUnmergedPending = () => {
  pendingWriteChain = pendingWriteChain
    .then(async () => {
      const pending = parsePending(await AsyncStorage.getItem(PENDING_KEY))
      let next = hidden.filter(
        (x) => touchedSinceHydration.has(x) || !pending.removed.includes(x),
      )
      for (const id of pending.added) {
        if (!touchedSinceHydration.has(id) && !next.includes(id)) {
          next = [...next, id]
        }
      }
      const changed =
        next.length !== hidden.length || next.some((x, i) => hidden[i] !== x)
      hidden = next
      await AsyncStorage.setItem(HIDDEN_KEY, JSON.stringify(hidden))
      await AsyncStorage.removeItem(PENDING_KEY)
      unmergedPendingOnDisk = false
      if (changed) emit()
    })
    .catch(() => {
      // still unreadable — keep the key; the next launch merges it
    })
}

const persistMain = () => {
  if (unmergedPendingOnDisk) {
    // A previous session's deltas may sit unread in the pending key. Never
    // delete them blind — recover them (newest user actions win), which also
    // persists the main list.
    recoverUnmergedPending()
    return
  }
  void AsyncStorage.setItem(HIDDEN_KEY, JSON.stringify(hidden)).catch(() => {
    // storage unavailable — memory still serves this session
  })
}

const hydrate = () => {
  if (hydrated || hydrationInFlight) return
  hydrationInFlight = true

  void AsyncStorage.getItem(HIDDEN_KEY)
    .then(async (rawMain) => {
      const stored = parseList(rawMain)
      // The pending key holds deltas from a previous session that never
      // finished hydrating. If it is unreadable, hydrate from the main list
      // alone and leave the key on disk for a later attempt.
      let pending: PendingDeltas = { added: [], removed: [] }
      let pendingReadable = true
      try {
        pending = parsePending(await AsyncStorage.getItem(PENDING_KEY))
      } catch {
        pendingReadable = false
      }

      // Recency order: disk pending (oldest) → this session's taps (newest).
      for (const id of pending.added) {
        if (!removed.has(id)) added.add(id)
      }
      for (const id of pending.removed) {
        if (!added.has(id)) removed.add(id)
      }

      const merged = stored.filter((x) => !removed.has(x))
      for (const id of added) {
        if (!merged.includes(id)) merged.push(id)
      }

      const hadDeltas = added.size > 0 || removed.size > 0
      hydrated = true
      hydrationInFlight = false
      unmergedPendingOnDisk = !pendingReadable
      touchedSinceHydration.clear()
      added.clear()
      removed.clear()
      hidden = merged
      emit()

      if (hadDeltas) {
        // Clear the pending key only once the merged list is safely on disk —
        // otherwise a failed main write would drop the deltas forever.
        void AsyncStorage.setItem(HIDDEN_KEY, JSON.stringify(merged))
          .then(() => {
            if (pendingReadable) clearPendingSequenced()
          })
          .catch(() => {
            // main write failed — the pending key still holds the deltas, so
            // the next launch merges them again
          })
      } else if (pendingReadable) {
        clearPendingSequenced()
      }
    })
    .catch(() => {
      // The main list is unreadable right now. Stay un-hydrated: main-key
      // persists remain disabled (nothing unread gets overwritten), memory +
      // the pending key keep serving the session, and the next subscribe
      // re-attempts hydration.
      hydrationInFlight = false
    })
}

export const subscribeHidden = (listener: () => void): (() => void) => {
  hydrate()
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

export const getHiddenSnapshot = (): readonly string[] => hidden

/** Hide a source from the feed everywhere until it's followed again. */
export const hideSource = (id: string): void => {
  if (hidden.includes(id)) return
  hidden = [...hidden, id]
  if (hydrated) {
    touchedSinceHydration.add(id)
    persistMain()
  } else {
    added.add(id)
    removed.delete(id)
    persistPending()
  }
  emit()
}

/** Bring a hidden source back (e.g. when the user follows it from search). */
export const unhideSource = (id: string): void => {
  if (!hidden.includes(id) && hydrated) return
  hidden = hidden.filter((x) => x !== id)
  if (hydrated) {
    touchedSinceHydration.add(id)
    persistMain()
  } else {
    removed.add(id)
    added.delete(id)
    persistPending()
  }
  emit()
}
