export default {
  intervals: {
    short: {
      day: 'dia',
      week: 'sem',
      month: 'mês',
      year: 'ano',
    },
  },
  benefitTypes: {
    custom: 'Personalizado',
    license_keys: 'Chaves de licença',
    github_repository: 'Acesso a repositório GitHub',
    discord: 'Convite do Discord',
    downloadables: 'Download de arquivos',
    meter_credit: 'Créditos de uso',
    feature_flag: 'Feature flag',
    slack_shared_channel: 'Canal partilhado do Slack',
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
    title: 'Adicionar método de pagamento',
    close: 'Fechar',
    submit: 'Adicionar método de pagamento',
    processing: 'A adicionar método de pagamento…',
    fallbackError: 'Algo correu mal. Tente novamente.',
    errors: {
      invalidRequest: 'Faltam parâmetros obrigatórios.',
      unauthorized: 'Sessão expirou.',
      processingFailed:
        'Não foi possível processar o método de pagamento. Tente novamente.',
      unknown: 'Algo correu mal.',
    },
  },
} as const
