'use client'

import {
  useApproveLaunch,
  useEditLaunch,
  useRejectLaunch,
  useReviewQueue,
  type LaunchEdit,
  type MyLaunch,
} from '@/hooks/queries/launches'
import { useT } from '@/providers/translate'
import {
  Button,
  Checkbox,
  Input,
  SegmentedControl,
  TextArea,
} from '@outception-com/orbit'
import { Box } from '@outception-com/orbit/Box'
import { Text } from '@outception-com/orbit/Text'
import { useState } from 'react'
import { LaunchRow } from './LaunchRow'
import { Field } from './SubmitLaunchForm'
import { todayKey } from './launchCopy'

const SLOTS_PER_DAY = 5

type Kicker = NonNullable<LaunchEdit['kicker']>

const ReviewItem = ({
  launch,
  slots,
}: {
  launch: MyLaunch
  slots: Record<string, number>
}) => {
  const t = useT()
  const approve = useApproveLaunch()
  const reject = useRejectLaunch()
  const edit = useEditLaunch()
  // The picker starts on the day the submitter asked for, if any and still
  // ahead; otherwise today.
  const [day, setDay] = useState(
    launch.day && launch.day >= todayKey() ? launch.day : todayKey(),
  )
  const [featured, setFeatured] = useState(false)
  const [note, setNote] = useState('')
  const [editing, setEditing] = useState(false)
  const [copy, setCopy] = useState<LaunchEdit>({
    name: launch.name,
    tagline: launch.tagline,
    description: launch.description,
    kicker: (['new', 'update', 'open source'] as const).includes(
      launch.kicker as Kicker,
    )
      ? (launch.kicker as Kicker)
      : 'new',
  })
  const [failed, setFailed] = useState(false)
  const taken = slots[day] ?? 0
  const busy = approve.isPending || reject.isPending || edit.isPending
  // The client resolves with an error field on a refused request rather
  // than throwing, so every action checks it and says so.
  const attempt = async (
    action: Promise<{ error?: unknown }>,
    onDone?: () => void,
  ) => {
    setFailed(false)
    const { error } = await action
    if (error) setFailed(true)
    else onDone?.()
  }
  return (
    <LaunchRow launch={launch}>
      <Box flexDirection="column" rowGap="m" paddingTop="s">
        <span className="meta-kicker">
          {t('launches.review.contact')}: {launch.contact_email} ·{' '}
          {t('launches.review.submitted')} {launch.created_at.slice(0, 10)}
        </span>
        {editing ? (
          <Box flexDirection="column" rowGap="s">
            <Field label={t('launches.submit.name')}>
              <Input
                value={copy.name ?? ''}
                onChange={(e) => setCopy({ ...copy, name: e.target.value })}
                maxLength={60}
              />
            </Field>
            <Field label={t('launches.submit.tagline')}>
              <Input
                value={copy.tagline ?? ''}
                onChange={(e) => setCopy({ ...copy, tagline: e.target.value })}
                maxLength={100}
              />
            </Field>
            <Field label={t('launches.submit.kicker')} group>
              <SegmentedControl<Kicker>
                options={[
                  { value: 'new', label: t('launches.kinds.new') },
                  { value: 'update', label: t('launches.kinds.update') },
                  {
                    value: 'open source',
                    label: t('launches.kinds.openSource'),
                  },
                ]}
                value={copy.kicker ?? 'new'}
                onChange={(value) => setCopy({ ...copy, kicker: value })}
              />
            </Field>
            <Field label={t('launches.submit.description')}>
              <TextArea
                value={copy.description ?? ''}
                onChange={(e) =>
                  setCopy({ ...copy, description: e.target.value })
                }
                maxLength={300}
                rows={3}
              />
            </Field>
            <Box flexDirection="row" columnGap="s" justifyContent="end">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setEditing(false)}
              >
                {t('launches.review.cancel')}
              </Button>
              <Button
                size="sm"
                disabled={busy}
                onClick={() =>
                  void attempt(
                    edit.mutateAsync({ id: launch.id, body: copy }),
                    () => setEditing(false),
                  )
                }
              >
                {t('launches.review.save')}
              </Button>
            </Box>
          </Box>
        ) : (
          <Box flexDirection="column" rowGap="m">
            <Box
              flexDirection="row"
              flexWrap="wrap"
              alignItems="end"
              columnGap="l"
              rowGap="s"
            >
              <Field label={t('launches.review.day')}>
                <Input
                  type="date"
                  value={day}
                  onChange={(e) => setDay(e.target.value)}
                />
              </Field>
              <Box paddingBottom="s">
                <Text variant="caption" color="muted" as="span">
                  {t('launches.review.slots', { taken })}
                </Text>
              </Box>
              <Box
                as="label"
                flexDirection="row"
                alignItems="center"
                columnGap="s"
                paddingBottom="s"
                cursor="pointer"
              >
                <Checkbox
                  checked={featured}
                  onCheckedChange={(checked) => setFeatured(checked === true)}
                />
                <Text variant="caption" as="span">
                  {t('launches.review.featured')}
                </Text>
              </Box>
            </Box>
            <Box
              flexDirection="row"
              flexWrap="wrap"
              alignItems="end"
              columnGap="l"
              rowGap="s"
            >
              <Box flexGrow={1} minWidth={240}>
                <Field label={t('launches.review.note')}>
                  <Input
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    maxLength={500}
                  />
                </Field>
              </Box>
              <Box flexDirection="row" columnGap="s" alignItems="center">
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={busy}
                  onClick={() =>
                    void attempt(reject.mutateAsync({ id: launch.id, note }))
                  }
                >
                  {t('launches.review.reject')}
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => setEditing(true)}
                >
                  {t('launches.review.edit')}
                </Button>
                <Button
                  size="sm"
                  disabled={busy || taken >= SLOTS_PER_DAY}
                  onClick={() =>
                    void attempt(
                      approve.mutateAsync({
                        id: launch.id,
                        body: { day, featured },
                      }),
                    )
                  }
                >
                  {t('launches.review.approve')}
                </Button>
              </Box>
            </Box>
          </Box>
        )}
        {failed ? (
          <Text variant="caption" color="danger">
            {t('launches.review.failed')}
          </Text>
        ) : null}
      </Box>
    </LaunchRow>
  )
}

/** The founder's queue: every submitted product, newest first, with the
 * slots taken per day so a pick never overfills one. */
export const ReviewQueue = () => {
  const t = useT()
  const { data, isLoading, isError } = useReviewQueue()
  return (
    <Box flexDirection="column" rowGap="l">
      {isLoading ? (
        <Text variant="caption" color="muted">
          {t('news.card.loading')}
        </Text>
      ) : null}
      {isError ? (
        <Text color="muted">{t('launches.review.notAllowed')}</Text>
      ) : null}
      {!isLoading && !isError && (data?.items.length ?? 0) === 0 ? (
        <Text color="muted">{t('launches.review.empty')}</Text>
      ) : null}
      {(data?.items ?? []).map((launch) => (
        <ReviewItem key={launch.id} launch={launch} slots={data?.slots ?? {}} />
      ))}
    </Box>
  )
}
