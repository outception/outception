import { GlassDialog } from '@/components/Shared/GlassDialog'
import { SourceRoster } from './SourceRoster'

/** The "Sources" palette as a frosted modal card over the wall, like the web's
 * search dialog: the card set stays mounted (and visible, blurred) behind it, and
 * tapping anywhere outside the card returns to the cards. */
export const SourceSearchSheet = ({
  visible,
  onClose,
  autoFocusSearch,
  suppressAutoFocus,
}: {
  visible: boolean
  onClose: () => void
  autoFocusSearch?: boolean
  /** First-launch welcome only: keep the keyboard down so the Starter card sets
   * are fully visible. Every user-initiated open keeps the autofocus. */
  suppressAutoFocus?: boolean
}) => (
  <GlassDialog visible={visible} onClose={onClose}>
    <SourceRoster
      onClose={onClose}
      autoFocusSearch={autoFocusSearch}
      suppressAutoFocus={suppressAutoFocus}
    />
  </GlassDialog>
)
