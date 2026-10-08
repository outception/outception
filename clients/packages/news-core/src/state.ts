/**
 * The signal state every card carries: how fresh and how trustworthy its
 * data is. Worst state wins when cards merge. `unavailable` is HTTP 502 and
 * `loading` never reaches the wire; both exist so the clients and the server
 * share one vocabulary.
 */

import type { schemas } from '@outception-com/client'

export type SignalState = schemas['SignalState']

export const SIGNAL_STATES: readonly SignalState[] = [
  'nominal',
  'loading',
  'degraded',
  'stale',
  'fallback',
  'unavailable',
]

// Higher is worse. `loading` sits below `degraded`: a card that is still
// loading is not yet known to be in trouble.
const SEVERITY: Readonly<Record<SignalState, number>> = {
  nominal: 0,
  loading: 1,
  degraded: 2,
  stale: 3,
  fallback: 4,
  unavailable: 5,
}

export const severity = (state: SignalState): number => SEVERITY[state]

export const isSignalState = (value: unknown): value is SignalState =>
  typeof value === 'string' && value in SEVERITY

/** The state a merged card carries: the worst of its parts. */
export const worstState = (states: readonly SignalState[]): SignalState => {
  let worst: SignalState = 'nominal'
  for (const state of states) {
    if (SEVERITY[state] > SEVERITY[worst]) worst = state
  }
  return worst
}

/** A `stale` or `degraded` card still paints its last data; only
 * `unavailable` has nothing to show. */
export const hasRenderableData = (state: SignalState): boolean =>
  state !== 'unavailable'

/** The tertiary word shown after the timestamp line. Healthy and loading
 * cards show nothing: the badge exists for trouble, never as decoration. */
export const stateWord = (
  state: SignalState,
): Exclude<SignalState, 'nominal' | 'loading'> | null =>
  state === 'nominal' || state === 'loading' ? null : state

/** The state a client derives from its own fetch, before a card arrives. */
export const stateFromFetch = (input: {
  loading: boolean
  error: boolean
  hasData: boolean
}): SignalState => {
  if (input.loading && !input.hasData) return 'loading'
  if (input.error) return input.hasData ? 'stale' : 'unavailable'
  return 'nominal'
}
