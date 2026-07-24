'use client'

import { useLocale, useT } from '@/providers/locale'
import {
  setLocaleOverride,
  subscribeLocaleOverride,
} from '@/utils/i18n/localeOverride'
import {
  getClientCountry,
  getFlagOverride,
  hasLocaleOverride,
} from '@/utils/i18n/shared'
import {
  type AcceptedLocale,
  LOCALE_NAMES,
  SUPPORTED_LOCALES,
  type SupportedLocale,
} from '@outception-com/i18n'
import {
  Command,
  CommandEmpty,
  CommandInput,
  CommandItem,
  CommandList,
} from '@outception-com/ui/components/ui/command'
import {
  Dialog,
  DialogContent,
  DialogTitle,
} from '@outception-com/ui/components/ui/dialog'
import { Check } from 'lucide-react'
import { useState, useSyncExternalStore } from 'react'
import { CountryFlag, Flag, hasCountryFlag } from './Flag'

const toSupported = (locale: AcceptedLocale): SupportedLocale => {
  if ((SUPPORTED_LOCALES as readonly string[]).includes(locale)) {
    return locale as SupportedLocale
  }
  const primary = locale.split('-')[0]
  return (
    (SUPPORTED_LOCALES as readonly string[]).includes(primary) ? primary : 'en'
  ) as SupportedLocale
}

// English content is the same everywhere, but readers identify with their own
// country's flag — so English is offered under each of the main English-speaking
// flags. Every entry selects the `en` locale; only the flag differs.
const ENGLISH_VARIANTS: { country: string; label: string }[] = [
  { country: 'US', label: 'English (US)' },
  { country: 'GB', label: 'English (UK)' },
  { country: 'IE', label: 'English (Ireland)' },
  { country: 'AU', label: 'English (Australia)' },
  { country: 'CA', label: 'English (Canada)' },
  { country: 'NZ', label: 'English (New Zealand)' },
]

type PickerRow =
  | { kind: 'en'; country: string; label: string }
  | { kind: 'lang'; locale: SupportedLocale }

const PICKER_ROWS: PickerRow[] = [
  ...ENGLISH_VARIANTS.map((v) => ({
    kind: 'en' as const,
    country: v.country,
    label: v.label,
  })),
  ...(SUPPORTED_LOCALES as readonly SupportedLocale[])
    .filter((l) => l !== 'en')
    .map((locale) => ({ kind: 'lang' as const, locale })),
]

/** A flag picker for the UI language, overriding auto-detection (browser + IP
 * country) — e.g. an English speaker on holiday in Japan. The nav pill opens a
 * search dialog styled like the "More" source palette; picking a flag sets the
 * language and closes. */
export const LanguagePicker = () => {
  const active = toSupported(useLocale())
  const t = useT()
  const [open, setOpen] = useState(false)

  // Show the visitor's detected-country flag (Ireland → 🇮🇪) while their locale
  // is auto-detected; once they explicitly pick a language, show that language's
  // flag instead. useSyncExternalStore (subscribed to the override store) keeps
  // the first client render matching the static shell (server snapshot: null →
  // language flag) before swapping — no hydration mismatch, no effect.
  const flagCountry = useSyncExternalStore(
    subscribeLocaleOverride,
    () => {
      // A flag chosen alongside an English variant wins; otherwise the visitor's
      // detected-country flag while their locale is still auto-detected.
      const chosen = getFlagOverride()
      if (chosen) return hasCountryFlag(chosen) ? chosen : null
      const country = hasLocaleOverride() ? null : getClientCountry()
      return country && hasCountryFlag(country) ? country : null
    },
    () => null,
  )

  // Which English-variant row gets the check: the reader's picked/detected
  // country if it's one we offer, else the US default.
  const activeEnglishCountry = getFlagOverride() ?? getClientCountry() ?? 'US'

  const choose = (locale: SupportedLocale, country?: string) => {
    setLocaleOverride(locale, country)
    setOpen(false)
  }

  return (
    <>
      <button
        type="button"
        aria-label="Change language"
        aria-expanded={open}
        onClick={() => setOpen(true)}
        className="flex cursor-pointer items-center gap-1 rounded-xl px-3 py-1 [color:color-mix(in_srgb,var(--color-ink)_55%,transparent)] transition-colors hover:[color:var(--color-ink)] dark:[color:color-mix(in_srgb,var(--color-ink-night)_65%,transparent)] dark:hover:[color:var(--color-ink-night)]"
      >
        {flagCountry ? (
          <CountryFlag country={flagCountry} />
        ) : (
          <Flag locale={active} />
        )}
        <span className="text-xs uppercase">{active}</span>
      </button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent
          className="paper-search h-[52vh] max-h-[85vh] min-h-[360px] w-full max-w-xl overflow-hidden rounded-2xl border-0 p-0 sm:rounded-2xl md:h-[56vh] md:min-h-[440px]"
          aria-describedby={undefined}
        >
          <DialogTitle className="sr-only">
            {t('news.language.title')}
          </DialogTitle>
          <Command className="h-full rounded-3xl bg-transparent text-black dark:text-white">
            <CommandInput
              placeholder={t('news.language.placeholder')}
              wrapperClassName="rule-hairline px-4"
              className="border-0 bg-transparent shadow-none ring-0 focus:border-0 focus:ring-0 focus:outline-none"
            />
            <CommandList className="max-h-none flex-1">
              <CommandEmpty>{t('news.language.empty')}</CommandEmpty>
              {PICKER_ROWS.map((row) => {
                const isEn = row.kind === 'en'
                const locale: SupportedLocale = isEn ? 'en' : row.locale
                const label = isEn ? row.label : LOCALE_NAMES[locale]
                const code = isEn ? row.country : locale
                const checked = isEn
                  ? active === 'en' &&
                    row.country.toUpperCase() ===
                      activeEnglishCountry.toUpperCase()
                  : locale === active
                return (
                  <CommandItem
                    key={isEn ? `en-${row.country}` : locale}
                    value={`${label} ${code}`}
                    onSelect={() =>
                      choose(locale, isEn ? row.country : undefined)
                    }
                    className="mx-1 cursor-pointer rounded-xl px-3 py-2 data-[selected=true]:!bg-neutral-500/10 data-[selected=true]:!text-current"
                  >
                    <span className="mr-2">
                      {isEn ? (
                        <CountryFlag country={row.country} />
                      ) : (
                        <Flag locale={locale} />
                      )}
                    </span>
                    <span>{label}</span>
                    <span className="meta-kicker ml-2 uppercase">{code}</span>
                    {checked && <Check className="ml-auto h-4 w-4 fill-none" />}
                  </CommandItem>
                )
              })}
            </CommandList>
          </Command>
        </DialogContent>
      </Dialog>
    </>
  )
}
