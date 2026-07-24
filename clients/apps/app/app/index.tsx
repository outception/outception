import { NewsFeed } from '@/components/News/NewsFeed'
import { ACCOUNTS_ENABLED } from '@/utils/features'
import { Box } from '@/components/Shared/Box'
import LogoIcon from '@/components/Shared/OutceptionLogo'
import { Text } from '@/components/Shared/Text'
import { Touchable } from '@/components/Shared/Touchable'
import { cycleEdition } from '@/design-system/themeStore'
import { useT } from '@/providers/LocaleProvider'
import { useSession } from '@/providers/SessionProvider'
import { useRouter } from 'expo-router'
import { StatusBar, useColorScheme } from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'

export default function Home() {
  const { session } = useSession()
  const router = useRouter()
  const scheme = useColorScheme()
  const t = useT()

  return (
    <SafeAreaView style={{ flex: 1 }} edges={['top']}>
      <StatusBar
        barStyle={scheme === 'dark' ? 'light-content' : 'dark-content'}
      />
      <Box
        flexDirection="row"
        alignItems="center"
        justifyContent="space-between"
        paddingHorizontal="spacing-16"
        paddingVertical="spacing-12"
      >
        <Box flexDirection="row" alignItems="center" gap="spacing-8">
          {/* Tapping the logo cycles the theme edition (web logo-wheel parity). */}
          <Touchable
            onPress={cycleEdition}
            accessibilityLabel={t('news.mobile.changeTheme')}
          >
            <LogoIcon size={26} />
          </Touchable>
          <Text variant="titleLarge">{t('news.mobile.wall')}</Text>
        </Box>
        {ACCOUNTS_ENABLED ? (
          <Box flexDirection="row" alignItems="center" gap="spacing-8">
            {session ? (
              <Touchable onPress={() => router.push('/settings')}>
                <Box
                  paddingVertical="spacing-8"
                  paddingHorizontal="spacing-16"
                  borderRadius="border-radius-8"
                  backgroundColor="card"
                >
                  <Text variant="caption" color="text">
                    {t('news.mobile.settings')}
                  </Text>
                </Box>
              </Touchable>
            ) : (
              <Touchable onPress={() => router.push('/login')}>
                <Box
                  paddingVertical="spacing-8"
                  paddingHorizontal="spacing-16"
                  borderRadius="border-radius-8"
                  backgroundColor="monochromeInverted"
                >
                  <Text variant="caption" color="monochrome">
                    {t('news.mobile.signIn')}
                  </Text>
                </Box>
              </Touchable>
            )}
          </Box>
        ) : null}
      </Box>
      <NewsFeed />
    </SafeAreaView>
  )
}
