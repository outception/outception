'use strict'
const PNPM_VIRTUAL_STORE = /\.pnpm\/([^/]+)\/node_modules\//g

function stripPnpmPeerHashes(value) {
  return String(value).replace(PNPM_VIRTUAL_STORE, (_match, segment) => {
    // Package names may themselves contain underscores (string_decoder), so
    // the peer-hash suffix starts at the first "_" after the version "@".
    const versionStart = segment.indexOf('@', 1)
    const peerStart = segment.indexOf(
      '_',
      versionStart === -1 ? 0 : versionStart,
    )
    const base = peerStart === -1 ? segment : segment.slice(0, peerStart)
    return `.pnpm/${base}/node_modules/`
  })
}

function sourceIdentity(source) {
  const locator =
    source.filePath != null ? stripPnpmPeerHashes(source.filePath) : source.id
  // a source with no locator at all can only be told apart by its digest
  return JSON.stringify([source.type, locator ?? sourceDigest(source)])
}

function sourceDigest(source) {
  switch (source.type) {
    case 'contents':
      return stripPnpmPeerHashes(source.contents ?? '')
    case 'dir':
      return ''
    default:
      return source.hash ?? ''
  }
}

function indexByIdentity(fingerprint) {
  return new Map(
    fingerprint.sources.map((source) => [
      sourceIdentity(source),
      { digest: sourceDigest(source), source },
    ]),
  )
}

function diffFingerprints(baseline, candidate) {
  const before = indexByIdentity(baseline)
  const after = indexByIdentity(candidate)
  const changes = []

  for (const [identity, entry] of after) {
    const prior = before.get(identity)
    if (!prior) {
      changes.push({ kind: 'added', source: entry.source })
    } else if (prior.digest !== entry.digest) {
      changes.push({ kind: 'modified', source: entry.source })
    }
  }

  for (const [identity, entry] of before) {
    if (!after.has(identity)) {
      changes.push({ kind: 'removed', source: entry.source })
    }
  }

  return changes
}

module.exports = {
  stripPnpmPeerHashes,
  sourceIdentity,
  sourceDigest,
  diffFingerprints,
}
