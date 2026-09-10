import { api } from '@/utils/client'
import { schemas, unwrap } from '@outception-com/client'

export type PromotedSlot = schemas['PromotedSlot']

/** Synthetic card set id for the Promoted card. Never collides with a real
 * source id (source ids are registry slugs; this one is reserved). */
export const PROMOTED_CARD_ID = 'promoted'

export const promotedApi = {
  active: () => unwrap(api.GET('/v1/promoted/active')),
}
