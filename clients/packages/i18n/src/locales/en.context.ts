// Translator notes for keys in en.ts that are ambiguous on their own. Read by
// scripts/translate.ts only; nothing here is bundled.
import type { TranslationKey } from '../types'

const context: Partial<Record<TranslationKey, string>> = {
  'ordinal.zero':
    'Ordinal suffix for the "zero" category of Intl.PluralRules (type: ordinal). Appended to a number to form ordinals. Provide the suffix only, the number is prepended automatically. For locales where all ordinals use the same suffix (e.g. German "1.", "2."), set every key to the same value. Not used in English.',
  'ordinal.one':
    'Ordinal suffix for the "one" category of Intl.PluralRules (type: ordinal). Appended to a number to form ordinals (e.g. 1st, 21st, 31st in English). Provide the suffix only, the number is prepended automatically. For locales where all ordinals use the same suffix (e.g. German "1.", "2."), set every key to the same value.',
  'ordinal.two':
    'Ordinal suffix for the "two" category of Intl.PluralRules (type: ordinal). Appended to a number to form ordinals (e.g. 2nd, 22nd in English). Provide the suffix only, the number is prepended automatically.',
  'ordinal.few':
    'Ordinal suffix for the "few" category of Intl.PluralRules (type: ordinal). Appended to a number to form ordinals (e.g. 3rd, 23rd in English). Provide the suffix only, the number is prepended automatically.',
  'ordinal.many':
    'Ordinal suffix for the "many" category of Intl.PluralRules (type: ordinal). Appended to a number to form ordinals. Provide the suffix only, the number is prepended automatically. Not used in English.',
  'ordinal.other':
    'Ordinal suffix for the "other" (default/fallback) category of Intl.PluralRules (type: ordinal). Appended to a number to form ordinals (e.g. 4th, 5th, 11th in English). Provide the suffix only, the number is prepended automatically.',
}

export default context
