export default {
  intervals: {
    short: {
      day: 'dg',
      week: 'wk',
      month: 'mnd',
      year: 'jr',
    },
  },
  benefitTypes: {
    custom: 'Aangepast',
    license_keys: 'Licentiesleutels',
    github_repository: 'Toegang tot GitHub-repository',
    discord: 'Discord-uitnodiging',
    downloadables: 'Bestandsdownloads',
    meter_credit: 'Verbruikstegoed',
    feature_flag: 'Feature flag',
    slack_shared_channel: 'Gedeeld Slack-kanaal',
  },
  ordinal: {
    zero: 'de',
    one: 'e',
    two: 'e',
    few: 'e',
    many: 'e',
    other: 'e',
  },
  embedPaymentMethod: {
    title: 'Betaalmethode toevoegen',
    close: 'Sluiten',
    submit: 'Betaalmethode toevoegen',
    processing: 'Betaalmethode toevoegen…',
    fallbackError: 'Er is iets misgegaan. Probeer het opnieuw.',
    errors: {
      invalidRequest: 'Vereiste parameters ontbreken.',
      unauthorized: 'Sessie verlopen.',
      processingFailed:
        'De betaalmethode kon niet worden verwerkt. Probeer het opnieuw.',
      unknown: 'Er is iets misgegaan.',
    },
  },
} as const
