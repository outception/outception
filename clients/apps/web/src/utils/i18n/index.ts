import { getTranslations, type Translations } from '@outception-com/i18n'

export * from './shared'

/** Page/tab `<title>` for a server component's metadata. */
export function metaTitle(key: keyof Translations['meta']): string {
  return getTranslations().meta[key]
}
