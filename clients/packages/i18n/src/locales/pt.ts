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
    slack_shared_channel: 'Canal compartilhado do Slack',
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
    title: 'Adicionar forma de pagamento',
    close: 'Fechar',
    submit: 'Adicionar forma de pagamento',
    processing: 'Adicionando forma de pagamento…',
    fallbackError: 'Algo deu errado. Tente novamente.',
    errors: {
      invalidRequest: 'Parâmetros obrigatórios ausentes.',
      unauthorized: 'Sessão expirada.',
      processingFailed:
        'Não foi possível processar a forma de pagamento. Tente novamente.',
      unknown: 'Algo deu errado.',
    },
  },
} as const
