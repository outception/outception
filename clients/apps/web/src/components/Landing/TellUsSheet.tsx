'use client'

import { useT } from '@/providers/translate'
import { api } from '@/utils/client'
import type { TranslationKey } from '@outception-com/i18n'
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

type Kind = 'feedback' | 'launch'

/** The strings each kind of sheet shows, by key under news. */
const COPY = {
  feedback: {
    label: 'news.tellUs.label',
    title: 'news.tellUs.title',
    intro: 'news.tellUs.intro',
    placeholder: 'news.tellUs.placeholder',
    sent: 'news.tellUs.sent',
  },
  launch: {
    label: 'news.products.submit',
    title: 'news.products.sheetTitle',
    intro: 'news.products.sheetIntro',
    placeholder: 'news.products.sheetPlaceholder',
    sent: 'news.products.sheetSent',
  },
} as const satisfies Record<
  Kind,
  Record<'label' | 'title' | 'intro' | 'placeholder' | 'sent', TranslationKey>
>

/** The "Tell us" sheet: one message, an optional address for a reply, no
 * account. Opened from the footer and the controls row; as the `launch`
 * kind it takes a product submission the same way while accounts are off. */
export const TellUsSheet = ({
  trigger = 'link',
  kind = 'feedback',
}: {
  trigger?: 'link' | 'pill' | 'headline'
  kind?: Kind
}) => {
  const copy = COPY[kind]
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
        context: { page: pathname ?? '/', kind },
      },
    })
    setPhase(error ? 'failed' : 'sent')
  }

  return (
    <>
      <button
        type="button"
        onClick={() => reset(true)}
        className={
          trigger === 'pill'
            ? 'ghost-pill'
            : trigger === 'headline'
              ? 'headline-link cursor-pointer'
              : 'cursor-pointer'
        }
      >
        <Text
          variant="caption"
          color={trigger === 'link' ? 'muted' : 'default'}
        >
          {t(copy.label)}
        </Text>
      </button>
      <Dialog open={open} onOpenChange={reset}>
        <DialogContent
          overlayClassName="paper-veil"
          className="paper-sheet w-full max-w-lg rounded-2xl border-0 p-6 text-black md:p-8 dark:text-white"
        >
          <DialogTitle className="sr-only">{t(copy.title)}</DialogTitle>
          <Box as="form" flexDirection="column" rowGap="l" onSubmit={submit}>
            <Box flexDirection="column" rowGap="xs">
              <Text variant="heading-xs" as="h2" serif>
                {t(copy.title)}
              </Text>
              <Text variant="caption" color="muted">
                {t(copy.intro)}
              </Text>
            </Box>
            {phase === 'sent' ? (
              <Text>{t(copy.sent)}</Text>
            ) : (
              <>
                <textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder={t(copy.placeholder)}
                  rows={5}
                  required
                  aria-label={t(copy.placeholder)}
                  className="paper-input w-full resize-y rounded-xl border-0 bg-transparent px-4 py-3 text-base outline-none placeholder:opacity-60"
                />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder={t('news.tellUs.emailPlaceholder')}
                  aria-label={t('news.tellUs.emailPlaceholder')}
                  className="paper-input w-full rounded-xl border-0 bg-transparent px-4 py-3 text-base outline-none placeholder:opacity-60"
                />
                {phase === 'failed' ? (
                  <Text variant="caption" color="danger">
                    {message.trim().length < MIN_CHARS
                      ? t('news.tellUs.tooShort')
                      : t('news.tellUs.failed')}
                  </Text>
                ) : null}
                <Box justifyContent="end">
                  <button
                    type="submit"
                    disabled={phase === 'sending'}
                    className="ghost-pill"
                    data-solid=""
                  >
                    {phase === 'sending'
                      ? t('news.tellUs.sending')
                      : t('news.tellUs.send')}
                  </button>
                </Box>
              </>
            )}
          </Box>
        </DialogContent>
      </Dialog>
    </>
  )
}
