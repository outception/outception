export default {
  intervals: {
    short: {
      day: 'g',
      week: 'h',
      month: 'a',
      year: 'y',
    },
  },
  benefitTypes: {
    license_keys: 'Lisans anahtarları',
    github_repository: 'GitHub deposu erişimi',
    discord: 'Discord daveti',
    downloadables: 'Dosya indirmeleri',
    custom: 'Özel',
    meter_credit: 'Ölçüm kredileri',
    feature_flag: 'Özellik bayrağı',
    slack_shared_channel: 'Paylaşılan Slack kanalı',
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
    title: 'Ödeme yöntemi ekle',
    close: 'Kapat',
    submit: 'Ödeme yöntemi ekle',
    processing: 'Ödeme yöntemi ekleniyor…',
    fallbackError: 'Bir sorun oluştu. Lütfen tekrar deneyin.',
    errors: {
      invalidRequest: 'Gerekli parametreler eksik.',
      unauthorized: 'Oturumun süresi doldu.',
      processingFailed: 'Ödeme yöntemi işlenemedi. Lütfen tekrar deneyin.',
      unknown: 'Bir sorun oluştu.',
    },
  },
} as const
