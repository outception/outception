import AsyncStorage from '@react-native-async-storage/async-storage'
import { createAsyncStoragePersister } from '@tanstack/query-async-storage-persister'
import type { PersistQueryClientOptions } from '@tanstack/react-query-persist-client'

/** Persist the query cache to the device so the last-loaded wall - followed
 * sources and their headlines - is readable with no network on next launch.
 * Only news queries are kept; anything account-scoped is dropped. */
const persister = createAsyncStoragePersister({
  storage: AsyncStorage,
  key: 'OUTCEPTION_NEWS_CACHE',
  // Each write re-stringifies EVERY persisted query on the JS thread, and
  // cache events fire constantly while the reader swipes (each promoted card
  // fetches). This is an offline nice-to-have - sub-second durability buys
  // nothing, so keep the stringify well away from the interaction hot path.
  throttleTime: 5000,
})

const MAX_AGE = 1000 * 60 * 60 * 24 // 24h; must stay below PERSISTED_GC_TIME

/** gcTime for the news queries that persist: restored entries must outlive the
 * persister's maxAge or they're garbage-collected right after hydrating.
 * Applied per-query in hooks/outception/news.ts - NOT as the queryClient
 * default, which would hold every query ever run in memory all session. */
export const PERSISTED_GC_TIME = 1000 * 60 * 60 * 25 // 25h

export const persistOptions: Omit<PersistQueryClientOptions, 'queryClient'> = {
  persister,
  maxAge: MAX_AGE,
  // Bump when the persisted shape changes to invalidate stale caches on update.
  // v2: search queries no longer persist (see shouldDehydrateQuery) - discard
  // v1 blobs bloated by one entry per search keystroke.
  // v3: the full roster no longer persists - discard the multi-megabyte v2
  // blobs, which on Android exceed AsyncStorage's cursor window on restore.
  buster: 'news-v3',
  dehydrateOptions: {
    // Search is excluded: every ≥2-char prefix typed becomes its own cache
    // entry, so persisting them grows the blob (re-stringified on every write)
    // without bound and restores stale keystroke queries for 24h.
    // The full roster ('sources') is excluded too: it is multiple megabytes,
    // re-stringified on the JS thread on every write, and big enough to blow
    // Android's SQLite cursor window so the whole restore fails. The deck
    // paints from the much smaller 'source-metas' query, which does persist.
    shouldDehydrateQuery: (query) =>
      query.queryKey[0] === 'news' &&
      query.queryKey[1] !== 'search' &&
      query.queryKey[1] !== 'sources' &&
      query.state.status === 'success',
  },
}
