'use client'

import { useT } from '@/providers/translate'
import { api } from '@/utils/client'
import { Button, Input, TextArea } from '@outception-com/orbit'
import { Box } from '@outception-com/orbit/Box'
import { Text } from '@outception-com/orbit/Text'
import {
  Dialog,
  DialogContent,
  DialogTitle,
} from '@outception-com/ui/components/ui/dialog'
import { usePathname } from 'next/navigation'
import { useState, type FormEvent } from 'react'

const MIN_CHARS = 3

type Phase = 'idle' | 'sending' | 'sent' | 'failed'

/** The "Tell us" sheet: one message, an optional address for a reply, no
 * account. Opened from the footer and the controls row. */
export const TellUsSheet = ({
  trigger = 'link',
}: {
  trigger?: 'link' | 'pill'
}) => {
  const t = useT()
  const pathname = usePathname()
  const [open, setOpen] = useState(false)
  const [message, setMessage] = useState('')
  const [email, setEmail] = useState('')
  const [phase, setPhase] = useState<Phase>('idle')

  const reset = (next: boolean) => {
    setOpen(next)
    if (!next) {
      setPhase('idle')
      setMessage('')
    }
  }

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    if (message.trim().length < MIN_CHARS) {
      setPhase('failed')
      return
    }
    setPhase('sending')
    const { error } = await api.POST('/v1/feedback', {
      body: {
        message: message.trim(),
        email: email.trim() || null,
        surface: 'web',
        context: { page: pathname ?? '/' },
      },
    })
    setPhase(error ? 'failed' : 'sent')
  }

  return (
    <>
      <button
        type="button"
        onClick={() => reset(true)}
        className={trigger === 'pill' ? 'ghost-pill' : 'cursor-pointer'}
      >
        <Text
          variant="caption"
          color={trigger === 'pill' ? 'default' : 'muted'}
        >
          {t('news.tellUs.label')}
        </Text>
      </button>
      <Dialog open={open} onOpenChange={reset}>
        <DialogContent className="paper-search w-full max-w-lg rounded-2xl border-0 p-6 text-black md:p-8 dark:text-white">
          <DialogTitle className="sr-only">
            {t('news.tellUs.title')}
          </DialogTitle>
          <Box as="form" flexDirection="column" rowGap="l" onSubmit={submit}>
            <Box flexDirection="column" rowGap="xs">
              <Text variant="heading-xs" as="h2" serif>
                {t('news.tellUs.title')}
              </Text>
              <Text variant="caption" color="muted">
                {t('news.tellUs.intro')}
              </Text>
            </Box>
            {phase === 'sent' ? (
              <Text>{t('news.tellUs.sent')}</Text>
            ) : (
              <>
                <TextArea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder={t('news.tellUs.placeholder')}
                  rows={5}
                  required
                  aria-label={t('news.tellUs.placeholder')}
                />
                <Input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder={t('news.tellUs.emailPlaceholder')}
                  aria-label={t('news.tellUs.emailPlaceholder')}
                />
                {phase === 'failed' ? (
                  <Text variant="caption" color="danger">
                    {message.trim().length < MIN_CHARS
                      ? t('news.tellUs.tooShort')
                      : t('news.tellUs.failed')}
                  </Text>
                ) : null}
                <Box justifyContent="end">
                  <Button type="submit" disabled={phase === 'sending'}>
                    {phase === 'sending'
                      ? t('news.tellUs.sending')
                      : t('news.tellUs.send')}
                  </Button>
                </Box>
              </>
            )}
          </Box>
        </DialogContent>
      </Dialog>
    </>
  )
}
