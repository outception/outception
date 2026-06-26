// https://docs.expo.dev/guides/using-eslint/
const { defineConfig } = require('eslint/config')
const expoConfig = require('eslint-config-expo/flat')
const noViewRule = require('./eslint-rules/no-view')
const noTextRule = require('./eslint-rules/no-text')
const noStyleSheetCreateRule = require('./eslint-rules/no-stylesheet-create')
const noImageRule = require('./eslint-rules/no-image')
const noFlatListRule = require('./eslint-rules/no-flatlist')
const noTouchableRule = require('./eslint-rules/no-touchable')
const noJsxLogicalAndRule = require('./eslint-rules/no-jsx-logical-and')
const noRestyleUseThemeRule = require('./eslint-rules/no-restyle-use-theme')
const noHardcodedSpacingRule = require('./eslint-rules/no-hardcoded-spacing')
const noHardcodedColorsRule = require('./eslint-rules/no-hardcoded-colors')
const noHardcodedDimensionsRule = require('./eslint-rules/no-hardcoded-dimensions')

module.exports = defineConfig([
  expoConfig,
  {
    ignores: ['dist/*'],
  },
  {
    plugins: {
      '@outception': {
        rules: {
          'no-view': noViewRule,
          'no-text': noTextRule,
          'no-stylesheet-create': noStyleSheetCreateRule,
          'no-image': noImageRule,
          'no-flatlist': noFlatListRule,
          'no-touchable': noTouchableRule,
          'no-jsx-logical-and': noJsxLogicalAndRule,
          'no-restyle-use-theme': noRestyleUseThemeRule,
          'no-hardcoded-spacing': noHardcodedSpacingRule,
          'no-hardcoded-colors': noHardcodedColorsRule,
          'no-hardcoded-dimensions': noHardcodedDimensionsRule,
        },
      },
    },
    rules: {
      '@outception/no-view': 'error',
      '@outception/no-text': 'error',
      '@outception/no-stylesheet-create': 'error',
      '@outception/no-image': 'error',
      '@outception/no-flatlist': 'error',
      '@outception/no-touchable': 'error',
      '@outception/no-jsx-logical-and': 'error',
      '@outception/no-restyle-use-theme': 'error',
      '@outception/no-hardcoded-spacing': 'error',
      '@outception/no-hardcoded-colors': 'error',
      '@outception/no-hardcoded-dimensions': 'error',
    },
  },
  {
    files: ['tooling/**/*.js'],
    languageOptions: {
      sourceType: 'commonjs',
      globals: {
        process: 'readonly',
        console: 'readonly',
        require: 'readonly',
        module: 'writable',
        __dirname: 'readonly',
      },
    },
    rules: {
      'no-console': 'off',
    },
  },
])
