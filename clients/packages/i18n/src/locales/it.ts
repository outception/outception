export default {
  intervals: {
    short: {
      day: 'g',
      week: 'sett',
      month: 'mese',
      year: 'anno',
    },
  },
  benefitTypes: {
    custom: 'Personalizzato',
    license_keys: 'Chiavi di licenza',
    github_repository: 'Accesso repository GitHub',
    discord: 'Invito Discord',
    downloadables: 'File scaricabili',
    meter_credit: 'Crediti a consumo',
    feature_flag: 'Feature flag',
    slack_shared_channel: 'Canale Slack condiviso',
  },
  ordinal: {
    zero: '°',
    one: '°',
    two: '°',
    few: '°',
    many: '°',
    other: '°',
  },
  embedPaymentMethod: {
    title: 'Aggiungi metodo di pagamento',
    close: 'Chiudi',
    submit: 'Aggiungi metodo di pagamento',
    processing: 'Aggiunta del metodo di pagamento…',
    fallbackError: 'Si è verificato un problema. Riprova.',
    errors: {
      invalidRequest: 'Parametri obbligatori mancanti.',
      unauthorized: 'Sessione scaduta.',
      processingFailed:
        'Impossibile elaborare il metodo di pagamento. Riprova.',
      unknown: 'Si è verificato un problema.',
    },
  },
} as const
