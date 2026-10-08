const { diffFingerprints, stripPnpmPeerHashes } = require('./fingerprint-diff')

describe('stripPnpmPeerHashes', () => {
  it('strips peer suffixes from virtual store paths', () => {
    expect(
      stripPnpmPeerHashes(
        'node_modules/.pnpm/expo-blur@15.0.7_react@19.0.0_abc123/node_modules/expo-blur/ios',
      ),
    ).toBe('node_modules/.pnpm/expo-blur@15.0.7/node_modules/expo-blur/ios')
  })

  it('keeps underscores that are part of the package name', () => {
    expect(
      stripPnpmPeerHashes(
        'node_modules/.pnpm/string_decoder@1.3.0/node_modules/string_decoder/lib',
      ),
    ).toBe(
      'node_modules/.pnpm/string_decoder@1.3.0/node_modules/string_decoder/lib',
    )
  })

  it('handles scoped packages', () => {
    expect(
      stripPnpmPeerHashes(
        'node_modules/.pnpm/@types+react@19.2.13_peer@1.0.0/node_modules/@types/react',
      ),
    ).toBe('node_modules/.pnpm/@types+react@19.2.13/node_modules/@types/react')
  })

  it('leaves paths outside the virtual store alone', () => {
    expect(stripPnpmPeerHashes('android/app/build.gradle')).toBe(
      'android/app/build.gradle',
    )
  })
})

describe('diffFingerprints', () => {
  const source = (overrides) => ({
    type: 'file',
    filePath: 'android/app/build.gradle',
    hash: 'aaa',
    ...overrides,
  })

  it('reports nothing when fingerprints match', () => {
    const fp = { sources: [source()] }
    expect(diffFingerprints(fp, { sources: [source()] })).toEqual([])
  })

  it('reports added, removed and modified sources', () => {
    const before = {
      sources: [source(), source({ filePath: 'ios/Podfile', hash: 'bbb' })],
    }
    const after = {
      sources: [
        source({ hash: 'ccc' }),
        source({ filePath: 'android/gradle.properties', hash: 'ddd' }),
      ],
    }
    const kinds = diffFingerprints(before, after).map((change) => change.kind)
    expect(kinds.sort()).toEqual(['added', 'modified', 'removed'])
  })

  it('ignores peer hash churn in file paths', () => {
    const before = {
      sources: [
        source({
          filePath:
            'node_modules/.pnpm/expo-blur@15.0.7_react@19.0.0/node_modules/expo-blur',
        }),
      ],
    }
    const after = {
      sources: [
        source({
          filePath:
            'node_modules/.pnpm/expo-blur@15.0.7_react@19.1.0/node_modules/expo-blur',
        }),
      ],
    }
    expect(diffFingerprints(before, after)).toEqual([])
  })

  it('ignores reason churn on an otherwise identical source', () => {
    const before = { sources: [source({ reasons: ['expoConfig'] })] }
    const after = { sources: [source({ reasons: ['easBuild'] })] }
    expect(diffFingerprints(before, after)).toEqual([])
  })
})
