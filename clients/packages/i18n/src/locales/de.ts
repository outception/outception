export default {
  intervals: {
    short: {
      day: 'T.',
      week: 'W.',
      month: 'M.',
      year: 'J',
    },
  },
  benefitTypes: {
    custom: 'Benutzerdefiniert',
    license_keys: 'Lizenzschlüssel',
    github_repository: 'GitHub-Repository-Zugang',
    discord: 'Discord-Einladung',
    downloadables: 'Dateidownloads',
    meter_credit: 'Verbrauchsguthaben',
    feature_flag: 'Feature-Flag',
    slack_shared_channel: 'Geteilter Slack-Kanal',
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
    title: 'Zahlungsmethode hinzufügen',
    close: 'Schließen',
    submit: 'Zahlungsmethode hinzufügen',
    processing: 'Zahlungsmethode wird hinzugefügt…',
    fallbackError: 'Etwas ist schiefgelaufen. Bitte versuchen Sie es erneut.',
    errors: {
      invalidRequest: 'Erforderliche Parameter fehlen.',
      unauthorized: 'Sitzung abgelaufen.',
      processingFailed:
        'Die Zahlungsmethode konnte nicht verarbeitet werden. Bitte versuchen Sie es erneut.',
      unknown: 'Etwas ist schiefgelaufen.',
    },
  },
} as const
