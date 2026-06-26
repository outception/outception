import { Box } from '@/components/Shared/Box'
import { Button } from '@/components/Shared/Button'
import { Input } from '@/components/Shared/Input'
import { Text } from '@/components/Shared/Text'
import { Touchable } from '@/components/Shared/Touchable'
import {
  PROMOTION_TOPICS,
  useCreatePromotion,
  usePromotionPricing,
} from '@/hooks/outception/promotions'
import { isOptionalHttpUrl } from '@/utils/promotions'
import { useTheme } from '@/design-system/useTheme'
import { useSession } from '@/providers/SessionProvider'
import { Redirect } from 'expo-router'
import * as WebBrowser from 'expo-web-browser'
import { useState } from 'react'
import { ScrollView } from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'

export default function Promote() {
  const theme = useTheme()
  const { session } = useSession()
  const { data: pricing } = usePromotionPricing()
  const createPromotion = useCreatePromotion()

  const [category, setCategory] = useState('news')
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const [link, setLink] = useState('')
  const [imageUrl, setImageUrl] = useState('')
  const [blocks, setBlocks] = useState('1')

  if (!session) {
    return <Redirect href="/login" />
  }

  const blockCount = Math.max(1, Number(blocks) || 1)
  const priceCents = (pricing?.price_cents ?? 1000) * blockCount
  const blockMinutes = pricing?.block_minutes ?? 10
  const linkInvalid = !isOptionalHttpUrl(link)
  const imageInvalid = !isOptionalHttpUrl(imageUrl)

  const onSubmit = () => {
    createPromotion.mutate(
      {
        category,
        title,
        body,
        link: link || null,
        image_url: imageUrl || null,
        blocks: blockCount,
      },
      {
        onSuccess: (checkout) => {
          WebBrowser.openBrowserAsync(checkout.url)
        },
      },
    )
  }

  return (
    <SafeAreaView style={{ flex: 1 }} edges={['bottom']}>
      <ScrollView
        contentContainerStyle={{
          padding: theme.spacing['spacing-16'],
          gap: theme.spacing['spacing-16'],
        }}
      >
        <Text variant="titleLarge">Promote a post</Text>
        <Text variant="body" color="subtext">
          Rent a topic&apos;s featured slot. Payment is handled securely by
          Outception.sh.
        </Text>

        <Box gap="spacing-8">
          <Text variant="caption" color="subtext">
            Topic
          </Text>
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={{ gap: theme.spacing['spacing-8'] }}
          >
            {PROMOTION_TOPICS.map((t) => (
              <Touchable key={t.id} onPress={() => setCategory(t.id)}>
                <Box
                  paddingVertical="spacing-6"
                  paddingHorizontal="spacing-16"
                  borderRadius="border-radius-999"
                  backgroundColor={category === t.id ? 'primary' : 'card'}
                >
                  <Text
                    variant="caption"
                    color={category === t.id ? 'monochromeInverted' : 'subtext'}
                  >
                    {t.label}
                  </Text>
                </Box>
              </Touchable>
            ))}
          </ScrollView>
        </Box>

        <Box gap="spacing-8">
          <Text variant="caption" color="subtext">
            Title
          </Text>
          <Input
            value={title}
            onChangeText={setTitle}
            placeholder="Your headline"
            maxLength={200}
          />
        </Box>

        <Box gap="spacing-8">
          <Text variant="caption" color="subtext">
            Body
          </Text>
          <Input
            value={body}
            onChangeText={setBody}
            placeholder="A sentence or two"
            multiline
            maxLength={2000}
          />
        </Box>

        <Box gap="spacing-8">
          <Text variant="caption" color="subtext">
            Link (optional)
          </Text>
          <Input
            value={link}
            onChangeText={setLink}
            placeholder="https://…"
            autoCapitalize="none"
            keyboardType="url"
          />
          {linkInvalid ? (
            <Text variant="caption" color="error">
              Enter a valid http(s) URL
            </Text>
          ) : null}
        </Box>

        <Box gap="spacing-8">
          <Text variant="caption" color="subtext">
            Image URL (optional)
          </Text>
          <Input
            value={imageUrl}
            onChangeText={setImageUrl}
            placeholder="https://…/image.png"
            autoCapitalize="none"
            keyboardType="url"
          />
          {imageInvalid ? (
            <Text variant="caption" color="error">
              Enter a valid http(s) URL
            </Text>
          ) : null}
        </Box>

        <Box gap="spacing-8">
          <Text variant="caption" color="subtext">
            Blocks ({blockMinutes} min each)
          </Text>
          <Input
            value={blocks}
            onChangeText={setBlocks}
            keyboardType="number-pad"
          />
        </Box>

        <Text variant="bodyMedium">
          Total: ${(priceCents / 100).toFixed(2)} for{' '}
          {blockCount * blockMinutes} min
        </Text>

        <Button
          onPress={onSubmit}
          loading={createPromotion.isPending}
          disabled={!title || !body || linkInvalid || imageInvalid}
        >
          Continue to payment
        </Button>
      </ScrollView>
    </SafeAreaView>
  )
}
