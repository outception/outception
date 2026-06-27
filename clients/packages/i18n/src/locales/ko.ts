export default {
  intervals: {
    short: {
      day: '일',
      week: '주',
      month: '월',
      year: '년',
    },
  },
  benefitTypes: {
    custom: '사용자 지정',
    license_keys: '라이선스 키',
    github_repository: 'GitHub 레포 액세스',
    discord: 'Discord 초대',
    downloadables: '파일 다운로드',
    meter_credit: '사용량 크레딧',
    feature_flag: '기능 플래그',
    slack_shared_channel: '공유 Slack 채널',
  },
  ordinal: {
    zero: '번째',
    one: '번째',
    two: '번째',
    few: '번째',
    many: '번째',
    other: '번째',
  },
  embedPaymentMethod: {
    title: '결제 수단 추가',
    close: '닫기',
    submit: '결제 수단 추가',
    processing: '결제 수단 추가 중…',
    fallbackError: '문제가 발생했습니다. 다시 시도해 주세요.',
    errors: {
      invalidRequest: '필수 매개변수가 없습니다.',
      unauthorized: '세션이 만료되었습니다.',
      processingFailed: '결제 수단을 처리할 수 없습니다. 다시 시도해 주세요.',
      unknown: '문제가 발생했습니다.',
    },
  },
} as const
