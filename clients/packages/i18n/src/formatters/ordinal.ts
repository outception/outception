import { getTranslations } from '../index'

const rules = new Intl.PluralRules('en', { type: 'ordinal' })

export function formatOrdinal(number: number): string {
  const category = rules.select(number)
  const t = getTranslations()
  const suffix =
    t.ordinal[category as keyof typeof t.ordinal] ?? t.ordinal.other
  return `${number}${suffix}`
}
