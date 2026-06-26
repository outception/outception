'use client'

import { toast } from '@/components/Toast/use-toast'
import {
  useCreatePromotion,
  usePromotionPricing,
} from '@/hooks/queries/promotions'
import { extractApiErrorMessage } from '@/utils/api/errors'
import { isOptionalHttpUrl, PROMOTION_TOPICS } from '@/utils/promotions'
import { Button, Input, Modal, Text, TextArea } from '@outception-com/orbit'
import { Box } from '@outception-com/orbit/Box'
import { useState } from 'react'
import { Controller, useForm, useWatch } from 'react-hook-form'

const URL_ERROR = 'Enter a valid http(s) URL'

const BODY_MAX = 2000

interface ComposeForm {
  category: string
  title: string
  body: string
  link: string
  blocks: number
}

const ComposePromotionForm = ({ hide }: { hide: () => void }) => {
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
            title: 'Could not start checkout',
            description: extractApiErrorMessage(
              error as { detail?: unknown },
              'You may need to sign in, or promotions are not configured.',
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
        Promote a post
      </Text>
      <Text color="muted">
        Rent the featured slot for a topic. Payment is handled securely by
        Outception.sh.
      </Text>

      <Box flexDirection="column" rowGap="s">
        <Text variant="caption">Topic</Text>
        <Controller
          control={control}
          name="category"
          render={({ field }) => (
            <select
              {...field}
              className="dark:border-outception-700 dark:bg-outception-800 h-10 rounded-xl border border-gray-200 bg-white px-3 text-sm dark:text-white"
            >
              {PROMOTION_TOPICS.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.label}
                </option>
              ))}
            </select>
          )}
        />
      </Box>

      <Box flexDirection="column" rowGap="s">
        <Text variant="caption">Title</Text>
        <Controller
          control={control}
          name="title"
          rules={{ required: true, maxLength: 200 }}
          render={({ field }) => (
            <Input {...field} placeholder="Your headline" maxLength={200} />
          )}
        />
      </Box>

      <Box flexDirection="column" rowGap="s">
        <Text variant="caption">Body</Text>
        <Controller
          control={control}
          name="body"
          rules={{ required: true, maxLength: BODY_MAX }}
          render={({ field }) => (
            <TextArea
              {...field}
              placeholder="A sentence or two about what you're promoting"
              maxLength={BODY_MAX}
            />
          )}
        />
      </Box>

      <Box flexDirection="column" rowGap="s">
        <Text variant="caption">Link (optional)</Text>
        <Controller
          control={control}
          name="link"
          rules={{ validate: (v) => isOptionalHttpUrl(v) || URL_ERROR }}
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
          <Text variant="caption">Blocks ({blockMinutes} min each)</Text>
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
          Total: ${(priceCents / 100).toFixed(2)} for {blocks * blockMinutes}{' '}
          min
        </Text>
      </Box>

      <Box flexDirection="row" columnGap="m" justifyContent="end">
        <Button variant="secondary" type="button" onClick={hide}>
          Cancel
        </Button>
        <Button
          type="button"
          loading={createPromotion.isPending}
          onClick={handleSubmit(onSubmit)}
        >
          Continue to payment
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
}: {
  trigger?: (open: () => void) => React.ReactNode
}) => {
  const [open, setOpen] = useState(false)
  return (
    <>
      {trigger ? (
        trigger(() => setOpen(true))
      ) : (
        <Button onClick={() => setOpen(true)}>Promote</Button>
      )}
      <Modal
        isShown={open}
        hide={() => setOpen(false)}
        title="Promote a post"
        modalContent={<ComposePromotionForm hide={() => setOpen(false)} />}
      />
    </>
  )
}

export default ComposePromotionDialog
