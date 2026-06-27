export default {
  intervals: {
    short: {
      day: 'd',
      week: 'v',
      month: 'mån',
      year: 'år',
    },
  },
  benefitTypes: {
    custom: 'Anpassad',
    license_keys: 'Licensnycklar',
    github_repository: 'Åtkomst till GitHub-repository',
    discord: 'Discord-inbjudan',
    downloadables: 'Filnedladdningar',
    meter_credit: 'Mätarkrediter',
    feature_flag: 'Feature flag',
    slack_shared_channel: 'Delad Slack-kanal',
  },
  ordinal: {
    zero: ':e',
    one: ':a',
    two: ':a',
    few: ':e',
    many: ':e',
    other: ':e',
  },
  embedPaymentMethod: {
    title: 'Lägg till betalningsmetod',
    close: 'Stäng',
    submit: 'Lägg till betalningsmetod',
    processing: 'Lägger till betalningsmetod…',
    fallbackError: 'Något gick fel. Försök igen.',
    errors: {
      invalidRequest: 'Saknar obligatoriska parametrar.',
      unauthorized: 'Sessionen har gått ut.',
      processingFailed:
        'Det gick inte att behandla betalningsmetoden. Försök igen.',
      unknown: 'Något gick fel.',
    },
  },
} as const
