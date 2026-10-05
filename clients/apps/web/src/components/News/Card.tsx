'use client'

import {
  isBriefingCardId,
  kindForId,
  WEATHER_STRIP_ID,
  type CardKind,
  type SourceMeta,
} from '@outception-com/news-core'
import { BriefingCard } from './BriefingCard'
import { FeedCard } from './FeedCard'
import { TableCard } from './TableCard'

/** What the deck emits: an id, its kind, and the catalog entry when the
 * client holds it. The envelope carries the entry too, so a card without a
 * local meta still paints once it loads. */
export interface CardDescriptor {
  id: string
  kind: CardKind
  meta?: SourceMeta
}

/** The descriptor for a deck id, or null when nothing can be painted: the
 * strip attaches to other cards and never stands alone, and an unknown
 * source id without a meta has no name to show. */
export const descriptorFor = (
  id: string,
  meta?: SourceMeta,
): CardDescriptor | null => {
  if (isBriefingCardId(id)) return { id, kind: 'briefing' }
  if (id === WEATHER_STRIP_ID) return null
  if (!meta || meta.type === 'game') return null
  return { id, kind: kindForId(id, meta.type), meta }
}

export interface CardProps {
  card: CardDescriptor
  /** The top card: it polls and takes the pointer. */
  active?: boolean
  /** One swipe ahead: fetches once so it arrives painted, but does not poll. */
  upcoming?: boolean
  /** The "why this card" line. */
  why?: string | null
  /** A shared story to open inside this card when it holds it. */
  storyId?: string | null
}

/** One card component, switching on kind. */
export const Card = ({ card, ...rest }: CardProps) => {
  switch (card.kind) {
    case 'table':
      return <TableCard card={card} {...rest} />
    case 'briefing':
      return <BriefingCard card={card} {...rest} />
    default:
      return <FeedCard card={card} {...rest} />
  }
}
