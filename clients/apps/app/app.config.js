// Google's public test app IDs by default; real ones come from env vars set
// per build profile in eas.json.

const plugins = [
  [
    'expo-build-properties',
    {
      android: {
        // R8 shrinking; RN/Expo libs ship their own keep rules
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
  'expo-quick-actions',
]

module.exports = {
  expo: {
    name: 'Outception',
    slug: 'outception-app',
    // runtimeVersion follows appVersion, so this has to track package.json
    version: require('./package.json').version,
    orientation: 'portrait',
    icon: './assets/images/icon.png',
    scheme: 'outception',
    // 'dark' pins AppCompatDelegate to MODE_NIGHT_YES and breaks useColorScheme()
    userInterfaceStyle: 'automatic',
    // SDK 54 edge-to-edge scrim draws a grey band under the nav bar otherwise
    androidNavigationBar: { enforceContrast: false },
    newArchEnabled: true,
    owner: 'outception-app',
    ios: {
      appleTeamId: 'PFQXM32538',
      supportsTablet: false,
      bundleIdentifier: 'com.outception.Outception',
      infoPlist: {
        ITSAppUsesNonExemptEncryption: false,
      },
      icon: './assets/images/ios-dark.png',
      entitlements: {
        'com.apple.developer.applesignin': ['Default'],
      },
      associatedDomains: [
        'applinks:outception.godetour.link',
        'applinks:outception.com',
      ],
    },
    android: {
      adaptiveIcon: {
        foregroundImage: './assets/images/adaptive-icon.png',
        // Native build-time value — Expo config can't reference theme tokens.
        // eslint-disable-next-line @outception/no-hardcoded-colors
        backgroundColor: '#0D0E10',
      },
      package: 'com.outception.Outception',
      // Nothing reads location; block both so a transitive lib can't add them.
      blockedPermissions: [
        'android.permission.ACCESS_COARSE_LOCATION',
        'android.permission.ACCESS_FINE_LOCATION',
      ],
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
          // shared card links (https://outception.com/?card=<id>)
          // autoVerify needs assetlinks.json on outception.com with our
          // signing cert — until then Android shows the app chooser
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
      // bump package.json whenever a native module is added, or an OTA can
      // reach an older binary and crash ('fingerprint' would automate this
      // but fails EAS's expo-updates configure step on this project)
      policy: 'appVersion',
    },
    updates: {
      url: 'https://u.expo.dev/d49bc2f6-e86b-4c89-beab-8edfb0b87ed4',
      checkAutomatically: 'ON_LOAD',
      // anything > 0 blocks cold start on the manifest fetch (black splash);
      // updates still download in the background and apply next launch
      fallbackToCacheTimeout: 0,
    },
  },
}
