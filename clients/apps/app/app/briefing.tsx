import { BriefingScreen } from '@/components/News/BriefingScreen'
import { Box } from '@/components/Shared/Box'
import { Text } from '@/components/Shared/Text'
import { Touchable } from '@/components/Shared/Touchable'
import { useT } from '@/providers/translate'
import { useLocalSearchParams, useRouter } from 'expo-router'
import { SafeAreaView } from 'react-native-safe-area-context'

/** The briefing screen the third pill opens; `?profile=` picks the profile. */
export default function Briefing() {
  const t = useT()
  const router = useRouter()
  const { profile } = useLocalSearchParams<{ profile?: string }>()
  return (
    <Box flex={1}>
      <SafeAreaView style={{ flex: 1 }} edges={['top', 'bottom']}>
        <Box
          flexDirection="row"
          alignItems="center"
          paddingHorizontal="spacing-16"
          paddingTop="spacing-8"
        >
          <Touchable onPress={() => router.back()}>
            <Text variant="caption" color="subtext">
              {t('news.briefing.back')}
            </Text>
          </Touchable>
        </Box>
        <BriefingScreen
          profile={typeof profile === 'string' ? profile : undefined}
          onProfile={(next) => router.setParams({ profile: next })}
        />
      </SafeAreaView>
    </Box>
  )
}
