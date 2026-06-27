export default {
  intervals: {
    short: {
      day: '日',
      week: '週',
      month: '月',
      year: '年',
    },
  },
  benefitTypes: {
    license_keys: 'ライセンスキー',
    github_repository: 'GitHubリポジトリへのアクセス',
    discord: 'Discord招待',
    downloadables: 'ファイルダウンロード',
    custom: 'カスタム',
    meter_credit: 'メータークレジット',
    feature_flag: '機能フラグ',
    slack_shared_channel: 'Slack共有チャンネル',
  },
  ordinal: {
    one: '番目',
    two: '番目',
    few: '番目',
    other: '番目',
    zero: '番目',
    many: '番目',
  },
  embedPaymentMethod: {
    title: '支払い方法を追加',
    close: '閉じる',
    submit: '支払い方法を追加',
    processing: '支払い方法を追加しています…',
    fallbackError: '問題が発生しました。もう一度お試しください。',
    errors: {
      invalidRequest: '必要なパラメータが不足しています。',
      unauthorized: 'セッションの有効期限が切れました。',
      processingFailed:
        '支払い方法を処理できませんでした。もう一度お試しください。',
      unknown: '問題が発生しました。',
    },
  },
} as const
