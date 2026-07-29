const { getSentryExpoConfig } = require('@sentry/react-native/metro')

const config = getSentryExpoConfig(__dirname)

// pnpm monorepo React dedup: the shared @outception-com/i18n package carries a
// nested react (the web app pins a newer 19.x than Expo's SDK pin), so Metro
// could otherwise pull two React copies into the bundle → "Invalid hook call".
// Force `react` and its subpaths to always resolve to THIS app's single copy.
const upstreamResolveRequest = config.resolver.resolveRequest
config.resolver.resolveRequest = (context, moduleName, platform) => {
  if (moduleName === 'react' || moduleName.startsWith('react/')) {
    return {
      type: 'sourceFile',
      filePath: require.resolve(moduleName, { paths: [__dirname] }),
    }
  }
  return upstreamResolveRequest
    ? upstreamResolveRequest(context, moduleName, platform)
    : context.resolveRequest(context, moduleName, platform)
}

module.exports = config
