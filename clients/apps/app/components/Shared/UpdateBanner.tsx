import { Box } from '@/components/Shared/Box'
import { Button } from '@/components/Shared/Button'
import { GlassSurface } from '@/components/Shared/GlassSurface'
import { Text } from '@/components/Shared/Text'
import { Touchable } from '@/components/Shared/Touchable'
import { useTheme } from '@/design-system/useTheme'
import { useT } from '@/providers/LocaleProvider'
import {
  checkForStoreUpdate,
  dismissStoreUpdate,
  type StoreUpdate,
} from '@/utils/appUpdate'
import { openExternalUrl } from '@/utils/news'
import { useEffect, useState } from 'react'
import { AppState } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

/** The app twin of the web cookie notice, repurposed as an update nudge: a
 * floating glass strip over the bottom of the wall telling a reader on an
 * older binary that a newer version is on the store. Per-version dismissal —
 * "Later" hides it until the next release ships. */
export const UpdateBanner = () => {
  const theme = useTheme()
  const t = useT()
  const insets = useSafeAreaInsets()
  const [update, setUpdate] = useState<StoreUpdate | null>(null)

  useEffect(() => {
    let mounted = true
    const check = () => {
      void checkForStoreUpdate().then((found) => {
        if (mounted && found) setUpdate(found)
      })
    }
    check()
    // iOS keeps the app alive for days, so a mount-only check could sail past
    // a release. Re-check whenever the app returns to the foreground — the
    // lookup cache in checkForStoreUpdate keeps this to one request an hour.
    const sub = AppState.addEventListener('change', (state) => {
      if (state === 'active') check()
    })
    return () => {
      mounted = false
      sub.remove()
    }
  }, [])

  if (update === null) return null
  const close = () => {
    dismissStoreUpdate(update.version)
    setUpdate(null)
  }

  return (
    <Box
      style={{
        position: 'absolute',
        left: 16,
        right: 16,
        bottom: insets.bottom + 16,
      }}
    >
      <GlassSurface radius={theme.borderRadii['border-radius-16']} />
      <Box
        flexDirection="row"
        alignItems="center"
        gap="spacing-12"
        padding="spacing-16"
      >
        <Text variant="caption" color="text" style={{ flex: 1 }}>
          {t('news.mobile.updateBanner.body', { version: update.version })}
        </Text>
        <Touchable
          onPress={close}
          accessibilityLabel={t('news.mobile.updateBanner.later')}
        >
          <Text variant="caption" color="subtext">
            {t('news.mobile.updateBanner.later')}
          </Text>
        </Touchable>
        <Button
          size="small"
          onPress={() => {
            openExternalUrl(update.url)
            close()
          }}
        >
          {t('news.mobile.updateBanner.update')}
        </Button>
      </Box>
    </Box>
  )
}
