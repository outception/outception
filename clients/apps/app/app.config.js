// AdMob application IDs. Default to Google's official TEST app IDs so dev
// builds work with no account; real ids come from the ADMOB_ANDROID_APP_ID /
// ADMOB_IOS_APP_ID env vars (set per build profile in eas.json). App IDs are
// public identifiers, safe to ship in the client.
const ADMOB_ANDROID_APP_ID =
  process.env.ADMOB_ANDROID_APP_ID || 'ca-app-pub-3940256099942544~3347511713'
const ADMOB_IOS_APP_ID =
  process.env.ADMOB_IOS_APP_ID || 'ca-app-pub-3940256099942544~1458002511'

const plugins = [
  'expo-router',
  [
    'expo-splash-screen',
    {
      image: './assets/images/splash-icon.png',
      imageWidth: 120,
      resizeMode: 'contain',
      // eslint-disable-next-line @outception/no-hardcoded-colors
      backgroundColor: '#0D0E10',
    },
  ],
  'expo-secure-store',
  'expo-font',
  [
    'expo-asset',
    {
      assets: ['./assets/images/login-background.jpg'],
    },
  ],
  'expo-web-browser',
  [
    '@sentry/react-native/expo',
    {
      url: 'https://sentry.io/',
      project: 'outception-app',
      organization: 'outception-com',
    },
  ],
  [
    'react-native-google-mobile-ads',
    {
      androidAppId: ADMOB_ANDROID_APP_ID,
      iosAppId: ADMOB_IOS_APP_ID,
    },
  ],
  [
    'expo-tracking-transparency',
    {
      userTrackingPermission:
        'This lets Outception show you more relevant ads.',
    },
  ],
]

module.exports = {
  expo: {
    name: 'Outception',
    slug: 'outception-app',
    version: '1.0.0',
    orientation: 'portrait',
    icon: './assets/images/icon.png',
    scheme: 'outception',
    userInterfaceStyle: 'dark',
    newArchEnabled: true,
    owner: 'outception-app',
    ios: {
      appleTeamId: '55U3YA3QTA',
      supportsTablet: false,
      bundleIdentifier: 'com.outception.Outception',
      infoPlist: {
        ITSAppUsesNonExemptEncryption: false,
      },
      icon: './assets/images/ios-dark.png',
      entitlements: {
        'com.apple.developer.applesignin': ['Default'],
      },
      associatedDomains: ['applinks:outception.godetour.link'],
    },
    android: {
      adaptiveIcon: {
        foregroundImage: './assets/images/adaptive-icon.png',
        // Native build-time value — Expo config can't reference theme tokens.
        // eslint-disable-next-line @outception/no-hardcoded-colors
        backgroundColor: '#0D0E10',
      },
      package: 'com.outception.Outception',
      scheme: 'outception',
      intentFilters: [
        {
          action: 'VIEW',
          autoVerify: true,
          data: [
            {
              scheme: 'https',
              host: 'outception.godetour.link',
              pathPrefix: '/baSjUTJtg8',
            },
          ],
          category: ['BROWSABLE', 'DEFAULT'],
        },
      ],
    },
    web: {
      bundler: 'metro',
      output: 'static',
      favicon: './assets/images/favicon.png',
    },
    plugins,
    experiments: {
      typedRoutes: true,
    },
    extra: {
      router: {
        origin: false,
        root: './app',
      },
      eas: {
        projectId: 'd49bc2f6-e86b-4c89-beab-8edfb0b87ed4',
      },
    },
    runtimeVersion: {
      policy: 'appVersion',
    },
    updates: {
      url: 'https://u.expo.dev/d49bc2f6-e86b-4c89-beab-8edfb0b87ed4',
      checkAutomatically: 'ON_LOAD',
      fallbackToCacheTimeout: 20000,
    },
  },
}
