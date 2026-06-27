export default {
  intervals: {
    short: {
      day: 'd',
      week: 'sem',
      month: 'm',
      year: 'a',
    },
  },
  benefitTypes: {
    custom: 'Personalizado',
    license_keys: 'Claves de licencia',
    github_repository: 'Acceso a repositorio de GitHub',
    discord: 'Invitación a Discord',
    downloadables: 'Descargas de archivos',
    meter_credit: 'Créditos de consumo',
    feature_flag: 'Feature flag',
    slack_shared_channel: 'Canal compartido de Slack',
  },
  ordinal: {
    zero: 'º',
    one: 'º',
    two: 'º',
    few: 'º',
    many: 'º',
    other: 'º',
  },
  embedPaymentMethod: {
    title: 'Añadir método de pago',
    close: 'Cerrar',
    submit: 'Añadir método de pago',
    processing: 'Añadiendo método de pago…',
    fallbackError: 'Algo ha ido mal. Inténtalo de nuevo.',
    errors: {
      invalidRequest: 'Faltan parámetros obligatorios.',
      unauthorized: 'La sesión ha caducado.',
      processingFailed:
        'No se ha podido procesar el método de pago. Inténtalo de nuevo.',
      unknown: 'Algo ha ido mal.',
    },
  },
} as const
