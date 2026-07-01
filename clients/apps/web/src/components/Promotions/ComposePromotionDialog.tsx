'use client'

import { toast } from '@/components/Toast/use-toast'
import {
  useCreatePromotion,
  usePromotionPricing,
} from '@/hooks/queries/promotions'
import { useT } from '@/providers/locale'
import { extractApiErrorMessage } from '@/utils/api/errors'
import { isOptionalHttpUrl, PROMOTION_TOPICS } from '@/utils/promotions'
import { Button, Input, Modal, Text, TextArea } from '@outception-com/orbit'
import { Box } from '@outception-com/orbit/Box'
import { useState } from 'react'
import { Controller, useForm, useWatch } from 'react-hook-form'

const BODY_MAX = 2000

interface ComposeForm {
  category: string
  title: string
  body: string
  link: string
  blocks: number
}

const ComposePromotionForm = ({ hide }: { hide: () => void }) => {
  const t = useT()
  const { data: pricing } = usePromotionPricing()
  const createPromotion = useCreatePromotion()
  const {
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<ComposeForm>({
    defaultValues: {
      category: 'news',
      title: '',
      body: '',
      link: '',
      blocks: 1,
    },
  })

  const watchedBlocks = useWatch({ control, name: 'blocks' })
  const blocks = Number(watchedBlocks) || 1
  const priceCents = (pricing?.price_cents ?? 1000) * blocks
  const blockMinutes = pricing?.block_minutes ?? 10

  const onSubmit = (data: ComposeForm) => {
    createPromotion.mutate(
      {
        category: data.category,
        title: data.title,
        body: data.body,
        link: data.link || null,
        blocks: Number(data.blocks) || 1,
      },
      {
        onSuccess: (checkout) => {
          window.location.href = checkout.url
        },
        onError: (error) => {
          toast({
            title: t('promotions.compose.errorTitle'),
            description: extractApiErrorMessage(
              error as { detail?: unknown },
              t('promotions.compose.errorBody'),
            ),
            variant: 'error',
          })
        },
      },
    )
  }

  return (
    <Box as="form" flexDirection="column" rowGap="l" padding="xl">
      <Text variant="heading-xs" as="h2">
        {t('promotions.compose.title')}
      </Text>
      <Text color="muted">{t('promotions.compose.subtitle')}</Text>

      <Box flexDirection="column" rowGap="s">
        <Text variant="caption">{t('promotions.compose.topic')}</Text>
        <Controller
          control={control}
          name="category"
          render={({ field }) => (
            <select
              {...field}
              className="dark:border-outception-700 dark:bg-outception-800 h-10 rounded-xl border border-gray-200 bg-white px-3 text-sm dark:text-white"
            >
              {PROMOTION_TOPICS.map((topic) => (
                <option key={topic.id} value={topic.id}>
                  {topic.label}
                </option>
              ))}
            </select>
          )}
        />
      </Box>

      <Box flexDirection="column" rowGap="s">
        <Text variant="caption">{t('promotions.compose.headline')}</Text>
        <Controller
          control={control}
          name="title"
          rules={{ required: true, maxLength: 200 }}
          render={({ field }) => (
            <Input
              {...field}
              placeholder={t('promotions.compose.headlinePlaceholder')}
              maxLength={200}
            />
          )}
        />
      </Box>

      <Box flexDirection="column" rowGap="s">
        <Text variant="caption">{t('promotions.compose.body')}</Text>
        <Controller
          control={control}
          name="body"
          rules={{ required: true, maxLength: BODY_MAX }}
          render={({ field }) => (
            <TextArea
              {...field}
              placeholder={t('promotions.compose.bodyPlaceholder')}
              maxLength={BODY_MAX}
            />
          )}
        />
      </Box>

      <Box flexDirection="column" rowGap="s">
        <Text variant="caption">{t('promotions.compose.link')}</Text>
        <Controller
          control={control}
          name="link"
          rules={{
            validate: (v) =>
              isOptionalHttpUrl(v) || t('promotions.compose.linkError'),
          }}
          render={({ field }) => (
            <Input {...field} placeholder="https://…" type="url" />
          )}
        />
        {errors.link ? (
          <Text variant="caption" color="danger">
            {errors.link.message}
          </Text>
        ) : null}
      </Box>

      <Box flexDirection="row" columnGap="m" alignItems="end">
        <Box flexDirection="column" rowGap="s">
          <Text variant="caption">
            {t('promotions.compose.blocks', { minutes: blockMinutes })}
          </Text>
          <Controller
            control={control}
            name="blocks"
            rules={{ required: true, min: 1, max: 144 }}
            render={({ field }) => (
              <Input {...field} type="number" min={1} max={144} />
            )}
          />
        </Box>
        <Text color="muted">
          {t('promotions.compose.total', {
            amount: `$${(priceCents / 100).toFixed(2)}`,
            minutes: blocks * blockMinutes,
          })}
        </Text>
      </Box>

      <Box flexDirection="row" columnGap="m" justifyContent="end">
        <Button variant="secondary" type="button" onClick={hide}>
          {t('promotions.compose.cancel')}
        </Button>
        <Button
          type="button"
          loading={createPromotion.isPending}
          onClick={handleSubmit(onSubmit)}
        >
          {t('promotions.compose.submit')}
        </Button>
      </Box>
    </Box>
  )
}

/** "Promote" entry point: opens the compose form in a modal. Pass `trigger` to
 * render a custom opener (e.g. the navbar's "Promo" pill); defaults to a
 * standard "Promote" button. */
export const ComposePromotionDialog = ({
  trigger,
  defaultOpen = false,
}: {
  trigger?: (open: () => void) => React.ReactNode
  defaultOpen?: boolean
}) => {
  const t = useT()
  const [open, setOpen] = useState(defaultOpen)
  return (
    <>
      {trigger ? (
        trigger(() => setOpen(true))
      ) : (
        <Button onClick={() => setOpen(true)}>{t('promotions.button')}</Button>
      )}
      <Modal
        isShown={open}
        hide={() => setOpen(false)}
        title={t('promotions.compose.title')}
        modalContent={<ComposePromotionForm hide={() => setOpen(false)} />}
      />
    </>
  )
}

export default ComposePromotionDialog
