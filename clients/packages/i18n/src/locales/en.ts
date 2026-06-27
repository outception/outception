export default {
  intervals: {
    short: {
      day: 'dy',
      week: 'wk',
      month: 'mo',
      year: 'yr',
    },
  },
  benefitTypes: {
    license_keys: 'License keys',
    github_repository: 'GitHub repository access',
    discord: 'Discord invite',
    downloadables: 'File downloads',
    custom: 'Custom',
    meter_credit: 'Meter credits',
    feature_flag: 'Feature flag',
    slack_shared_channel: 'Shared Slack channel',
  },
  ordinal: {
    zero: {
      value: '',
      _llmContext:
        'Ordinal suffix for the "zero" category of Intl.PluralRules (type: ordinal). Appended to a number to form ordinals. Provide the suffix only — the number is prepended automatically. For locales where all ordinals use the same suffix (e.g. German "1.", "2."), set every key to the same value. Not used in English.',
    },
    one: {
      value: 'st',
      _llmContext:
        'Ordinal suffix for the "one" category of Intl.PluralRules (type: ordinal). Appended to a number to form ordinals (e.g. 1st, 21st, 31st in English). Provide the suffix only — the number is prepended automatically. For locales where all ordinals use the same suffix (e.g. German "1.", "2."), set every key to the same value.',
    },
    two: {
      value: 'nd',
      _llmContext:
        'Ordinal suffix for the "two" category of Intl.PluralRules (type: ordinal). Appended to a number to form ordinals (e.g. 2nd, 22nd in English). Provide the suffix only — the number is prepended automatically.',
    },
    few: {
      value: 'rd',
      _llmContext:
        'Ordinal suffix for the "few" category of Intl.PluralRules (type: ordinal). Appended to a number to form ordinals (e.g. 3rd, 23rd in English). Provide the suffix only — the number is prepended automatically.',
    },
    many: {
      value: '',
      _llmContext:
        'Ordinal suffix for the "many" category of Intl.PluralRules (type: ordinal). Appended to a number to form ordinals. Provide the suffix only — the number is prepended automatically. Not used in English.',
    },
    other: {
      value: 'th',
      _llmContext:
        'Ordinal suffix for the "other" (default/fallback) category of Intl.PluralRules (type: ordinal). Appended to a number to form ordinals (e.g. 4th, 5th, 11th in English). Provide the suffix only — the number is prepended automatically.',
    },
  },
  embedPaymentMethod: {
    title: 'Add payment method',
    close: {
      value: 'Close',
      _llmContext:
        'aria-label for the close (X) button on the embedded payment method modal.',
    },
    submit: 'Add payment method',
    processing: 'Adding payment method…',
    fallbackError: 'Something went wrong. Please try again.',
    errors: {
      invalidRequest: 'Missing required parameters.',
      unauthorized: 'Session expired.',
      processingFailed:
        'Could not process the payment method. Please try again.',
      unknown: 'Something went wrong.',
    },
  },
  news: {
    tabs: {
      yourDeck: 'Your deck',
      trending: 'Trending',
      more: 'More',
      promo: 'Promo',
    },
    search: {
      placeholder: 'Search sources…',
      all: 'All',
      empty: 'No sources found.',
    },
    deck: {
      emptyHint: 'Your deck is empty. Open “More” to follow sources.',
      browse: 'Browse sources',
    },
    card: {
      updated: 'updated',
      failed: 'failed to load',
      loading: 'loading…',
      noHeadlines: 'No headlines right now.',
    },
    follow: {
      following: '★ Following',
      follow: '☆ Follow',
    },
    footer: '© Outception 2026',
  },
} as const
