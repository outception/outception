export default {
  intervals: {
    short: {
      day: 'j',
      week: 'sem',
      month: 'mois',
      year: 'an',
    },
  },
  benefitTypes: {
    custom: 'Personnalisé',
    license_keys: 'Clés de licence',
    github_repository: 'Accès au dépôt GitHub',
    discord: 'Invitation Discord',
    downloadables: 'Fichiers',
    meter_credit: 'Crédits prépayés',
    feature_flag: 'Accès à une fonctionnalité',
    slack_shared_channel: 'Canal Slack partagé',
  },
  ordinal: {
    zero: 'e',
    one: 'er',
    two: 'e',
    few: 'e',
    many: 'e',
    other: 'e',
  },
  embedPaymentMethod: {
    title: 'Ajouter un moyen de paiement',
    close: 'Fermer',
    submit: 'Ajouter un moyen de paiement',
    processing: 'Ajout du moyen de paiement…',
    fallbackError: 'Une erreur s’est produite. Veuillez réessayer.',
    errors: {
      invalidRequest: 'Paramètres obligatoires manquants.',
      unauthorized: 'La session a expiré.',
      processingFailed:
        'Impossible de traiter le moyen de paiement. Veuillez réessayer.',
      unknown: 'Une erreur s’est produite.',
    },
  },
} as const
