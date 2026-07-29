const BUNDLE_ID = 'com.outception.Outception'

const payloads = {
  headline: {
    'Simulator Target Bundle': BUNDLE_ID,
    aps: {
      alert: {
        title: 'World',
        body: 'Parliament passes revised budget after late-night vote',
      },
      sound: 'default',
      badge: 1,
    },
    body: {
      deepLink:
        'outception://news/article/517a341f-6df1-4d21-8c32-c236a7d4069d',
    },
  },

  sources: {
    'Simulator Target Bundle': BUNDLE_ID,
    aps: {
      alert: {
        title: 'New sources',
        body: '5 new sources match your deck',
      },
      sound: 'default',
    },
    body: {
      deepLink: 'outception://news/sources',
    },
  },

  plain: {
    'Simulator Target Bundle': BUNDLE_ID,
    aps: {
      alert: {
        title: 'Outception',
        body: 'Notification without a deep link',
      },
      sound: 'default',
    },
  },
}

module.exports = payloads
