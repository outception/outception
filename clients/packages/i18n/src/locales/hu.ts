export default {
  intervals: {
    short: {
      day: 'nap',
      week: 'hét',
      month: 'hó',
      year: 'év',
    },
  },
  benefitTypes: {
    custom: 'Egyedi',
    license_keys: 'Licenckulcsok',
    github_repository: 'GitHub repository hozzáférés',
    discord: 'Discord meghívó',
    downloadables: 'Fájlletöltések',
    meter_credit: 'Használat alapú kreditek',
    feature_flag: 'Feature flag',
    slack_shared_channel: 'Megosztott Slack-csatorna',
  },
  ordinal: {
    zero: '.',
    one: '.',
    two: '.',
    few: '.',
    many: '.',
    other: '.',
  },
  embedPaymentMethod: {
    title: 'Fizetési mód hozzáadása',
    close: 'Bezárás',
    submit: 'Fizetési mód hozzáadása',
    processing: 'Fizetési mód hozzáadása…',
    fallbackError: 'Valami hiba történt. Próbálja újra.',
    errors: {
      invalidRequest: 'Hiányzó kötelező paraméterek.',
      unauthorized: 'A munkamenet lejárt.',
      processingFailed:
        'A fizetési módot nem sikerült feldolgozni. Próbálja újra.',
      unknown: 'Valami hiba történt.',
    },
  },
} as const
