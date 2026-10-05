'use client'

import { useSubmitLaunch, type LaunchCreate } from '@/hooks/queries/launches'
import { useT } from '@/providers/translate'
import {
  Button,
  Input,
  SegmentedControl,
  TextArea,
} from '@outception-com/orbit'
import { Box } from '@outception-com/orbit/Box'
import { Text } from '@outception-com/orbit/Text'
import Link from 'next/link'
import { useState, type FormEvent } from 'react'

type Kicker = LaunchCreate['kicker']

/** The submit form: what the product is and where it lives. Every field
 * mirrors the server's limits; the founder reviews every submission. */
export const SubmitLaunchForm = () => {
  const t = useT()
  const submit = useSubmitLaunch()
  const [form, setForm] = useState<LaunchCreate>({
    name: '',
    tagline: '',
    url: '',
    logo_url: null,
    kicker: 'new',
    description: '',
    contact_email: '',
    preferred_day: null,
  })
  const [done, setDone] = useState(false)
  const [failed, setFailed] = useState(false)
  const set = <K extends keyof LaunchCreate>(key: K, value: LaunchCreate[K]) =>
    setForm((prev) => ({ ...prev, [key]: value }))

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setFailed(false)
    const { error } = await submit.mutateAsync({
      ...form,
      logo_url: form.logo_url || null,
      preferred_day: form.preferred_day || null,
    })
    if (error) setFailed(true)
    else setDone(true)
  }

  if (done) {
    return (
      <Box flexDirection="column" rowGap="m">
        <Text>{t('launches.submit.sent')}</Text>
        <Link href="/launches/mine" className="headline-link">
          <Text variant="caption" as="span">
            {t('launches.mine.title')}
          </Text>
        </Link>
      </Box>
    )
  }

  return (
    <Box
      as="form"
      flexDirection="column"
      rowGap="l"
      maxWidth={560}
      onSubmit={onSubmit}
    >
      <Box flexDirection="column" rowGap="xs">
        <Text variant="heading-xs" as="h1" serif>
          {t('launches.submit.title')}
        </Text>
        <Text variant="caption" color="muted">
          {t('launches.submit.intro')}
        </Text>
      </Box>
      <Field label={t('launches.submit.name')}>
        <Input
          value={form.name}
          onChange={(e) => set('name', e.target.value)}
          maxLength={60}
          required
        />
      </Field>
      <Field label={t('launches.submit.tagline')}>
        <Input
          value={form.tagline}
          onChange={(e) => set('tagline', e.target.value)}
          maxLength={100}
          required
        />
      </Field>
      <Field label={t('launches.submit.url')}>
        <Input
          type="url"
          value={form.url}
          onChange={(e) => set('url', e.target.value)}
          placeholder="https://"
          required
        />
      </Field>
      <Field label={t('launches.submit.logoUrl')}>
        <Input
          type="url"
          value={form.logo_url ?? ''}
          onChange={(e) => set('logo_url', e.target.value)}
          placeholder="https://"
        />
      </Field>
      <Field label={t('launches.submit.kicker')}>
        <SegmentedControl<Kicker>
          options={[
            { value: 'new', label: t('launches.kinds.new') },
            { value: 'update', label: t('launches.kinds.update') },
            { value: 'open source', label: t('launches.kinds.openSource') },
          ]}
          value={form.kicker}
          onChange={(value) => set('kicker', value)}
        />
      </Field>
      <Field label={t('launches.submit.description')}>
        <TextArea
          value={form.description}
          onChange={(e) => set('description', e.target.value)}
          maxLength={300}
          rows={3}
        />
      </Field>
      <Field label={t('launches.submit.contactEmail')}>
        <Input
          type="email"
          value={form.contact_email}
          onChange={(e) => set('contact_email', e.target.value)}
          required
        />
      </Field>
      <Field label={t('launches.submit.preferredDay')}>
        <Input
          type="date"
          value={form.preferred_day ?? ''}
          onChange={(e) => set('preferred_day', e.target.value)}
        />
      </Field>
      {failed ? (
        <Text variant="caption" color="danger">
          {t('launches.submit.failed')}
        </Text>
      ) : null}
      <Box justifyContent="end">
        <Button type="submit" disabled={submit.isPending}>
          {t('launches.submit.send')}
        </Button>
      </Box>
    </Box>
  )
}

export const Field = ({
  label,
  children,
}: {
  label: string
  children: React.ReactNode
}) => (
  <Box as="label" flexDirection="column" rowGap="xs">
    <Text variant="caption" color="muted" as="span">
      {label}
    </Text>
    {children}
  </Box>
)
