import { NewsFeed } from '@/components/News/NewsFeed'
import { Box } from '@/components/Shared/Box'
import { Text } from '@/components/Shared/Text'
import { Touchable } from '@/components/Shared/Touchable'
import { useSession } from '@/providers/SessionProvider'
import { openPromoteOnWeb } from '@/utils/promote'
import { useRouter } from 'expo-router'
import { StatusBar, useColorScheme } from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'

export default function Home() {
  const { session } = useSession()
  const router = useRouter()
  const scheme = useColorScheme()

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
        <Text variant="titleLarge">The Wall</Text>
        <Box flexDirection="row" alignItems="center" gap="spacing-8">
          {session ? (
            <>
              <Touchable onPress={() => router.push('/settings')}>
                <Box
                  paddingVertical="spacing-8"
                  paddingHorizontal="spacing-16"
                  borderRadius="border-radius-999"
                  backgroundColor="card"
                >
                  <Text variant="caption" color="text">
                    Settings
                  </Text>
                </Box>
              </Touchable>
              <Touchable onPress={() => router.push('/promotions')}>
                <Box
                  paddingVertical="spacing-8"
                  paddingHorizontal="spacing-16"
                  borderRadius="border-radius-999"
                  backgroundColor="card"
                >
                  <Text variant="caption" color="text">
                    My promos
                  </Text>
                </Box>
              </Touchable>
            </>
          ) : null}
          <Touchable
            onPress={() =>
              session ? openPromoteOnWeb() : router.push('/login')
            }
          >
            <Box
              paddingVertical="spacing-8"
              paddingHorizontal="spacing-16"
              borderRadius="border-radius-999"
              backgroundColor="monochromeInverted"
            >
              <Text variant="caption" color="monochrome">
                {session ? 'Promote' : 'Sign in'}
              </Text>
            </Box>
          </Touchable>
        </Box>
      </Box>
      <NewsFeed />
    </SafeAreaView>
  )
}
