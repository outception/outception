// AdMob application IDs. Default to Google's official TEST app IDs so dev
// builds work with no account; real ids come from the ADMOB_ANDROID_APP_ID /
// ADMOB_IOS_APP_ID env vars (set per build profile in eas.json). App IDs are
// public identifiers, safe to ship in the client.
const ADMOB_ANDROID_APP_ID =
  process.env.ADMOB_ANDROID_APP_ID || 'ca-app-pub-3940256099942544~3347511713'
const ADMOB_IOS_APP_ID =
  process.env.ADMOB_IOS_APP_ID || 'ca-app-pub-3940256099942544~1458002511'

const plugins = [
  [
    'expo-build-properties',
    {
      android: {
        // R8 code + resource shrinking: smaller download, and the mapping
        // file Play wants for readable crash traces. RN/Expo libraries ship
        // their own keep rules, so default shrinking is safe.
        enableMinifyInReleaseBuilds: true,
        enableShrinkResourcesInReleaseBuilds: true,
      },
    },
  ],
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
  [
    'expo-location',
    {
      locationWhenInUsePermission:
        'This lets Outception show weather for your exact location.',
    },
  ],
]

module.exports = {
  expo: {
    name: 'Outception',
    slug: 'outception-app',
    // Single source of truth: package.json. A hardcoded value here silently
    // diverges, and since runtimeVersion follows appVersion, a stale value both
    // blocks the next App Store submission and lets a new OTA target old
    // binaries that lack its native modules.
    version: require('./package.json').version,
    orientation: 'portrait',
    icon: './assets/images/icon.png',
    scheme: 'outception',
    // 'automatic', not 'dark': forcing dark makes expo-system-ui pin
    // AppCompatDelegate to MODE_NIGHT_YES, so useColorScheme() always reports
    // dark and the store's default 'system' tone can never follow the OS.
    userInterfaceStyle: 'automatic',
    // Edge-to-edge is on by default in SDK 54, and Expo's plugin enforces a
    // contrast scrim behind the navigation bar unless told otherwise — that
    // scrim reads as a grey band across the bottom of the full-bleed wall.
    androidNavigationBar: { enforceContrast: false },
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
      // expo-location always adds ACCESS_FINE_LOCATION; a weather card doesn't
      // justify precise location, and it's exactly what Play's permissions
      // review and the Data safety form scrutinise. Coarse is plenty.
      permissions: ['android.permission.ACCESS_COARSE_LOCATION'],
      blockedPermissions: ['android.permission.ACCESS_FINE_LOCATION'],
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
        {
          // Shared card links (https://outception.com/?card=<id>). Both apps'
          // share buttons emit this URL, but before this filter a recipient on
          // Android could only ever open it in a browser.
          // NOTE: autoVerify requires /.well-known/assetlinks.json on
          // outception.com carrying this app's signing-cert SHA-256; until that
          // is published Android shows the app chooser instead of opening
          // directly. The in-app handling works either way.
          action: 'VIEW',
          autoVerify: true,
          data: [{ scheme: 'https', host: 'outception.com' }],
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
      // Runtime version follows the app version, so BUMP package.json whenever
      // a native module is added — otherwise an OTA can reach an older binary
      // that lacks it and crash on launch. 1.6.0 forks away from the 1.5.0
      // builds that predate expo-blur / masked-view / expo-linear-gradient.
      // ('fingerprint' would automate this, but it failed EAS's "Configure
      // expo-updates" phase on this project.)
      policy: 'appVersion',
    },
    updates: {
      url: 'https://u.expo.dev/d49bc2f6-e86b-4c89-beab-8edfb0b87ed4',
      checkAutomatically: 'ON_LOAD',
      // 0, not a timeout: this is how long the native launcher blocks BEFORE
      // showing any UI while it fetches an OTA manifest. A non-zero value is a
      // black splash of up to that long on every cold start over mobile data.
      // The update still downloads in the background and applies next launch.
      fallbackToCacheTimeout: 0,
    },
  },
}
