export const SUPPORTED_LOCALES = ['en'] as const
export type SupportedLocale = (typeof SUPPORTED_LOCALES)[number]
export const DEFAULT_LOCALE = 'en' satisfies SupportedLocale

/** The app ships in English only. Kept as a named type so call sites read as
 * locale-aware where a future locale would slot in. */
export type AcceptedLocale = SupportedLocale
