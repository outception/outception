import { NewsFeed } from '@/components/News/NewsFeed'
import { Box } from '@/components/Shared/Box'
import { Text } from '@/components/Shared/Text'
import { Touchable } from '@/components/Shared/Touchable'
import { useSession } from '@/providers/SessionProvider'
import { useRouter } from 'expo-router'
import { StatusBar } from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'

export default function Home() {
  const { session } = useSession()
  const router = useRouter()

  return (
    <SafeAreaView style={{ flex: 1 }} edges={['top']}>
      <StatusBar barStyle="light-content" />
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
            onPress={() => router.push(session ? '/promote' : '/login')}
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
