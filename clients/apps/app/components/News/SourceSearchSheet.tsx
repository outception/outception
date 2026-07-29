import { GlassDialog } from '@/components/Shared/GlassDialog'
import { SourceRoster } from './SourceRoster'

/** The "Sources" palette as a frosted modal card over the wall, like the web's
 * search dialog: the deck stays mounted (and visible, blurred) behind it, and
 * tapping anywhere outside the card returns to the cards. */
export const SourceSearchSheet = ({
  visible,
  onClose,
  autoFocusSearch,
}: {
  visible: boolean
  onClose: () => void
  autoFocusSearch?: boolean
}) => (
  <GlassDialog visible={visible} onClose={onClose}>
    <SourceRoster onClose={onClose} autoFocusSearch={autoFocusSearch} />
  </GlassDialog>
)
