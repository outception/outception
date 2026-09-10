import { useTranslations } from '@outception-com/i18n'

/** The translate function: `const t = useT()`. The app ships in English only,
 * so this is a stable binding over the bundled string table. */
export const useT = () => useTranslations()
