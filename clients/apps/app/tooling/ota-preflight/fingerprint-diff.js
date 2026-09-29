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
    let base = peerStart === -1 ? segment : segment.slice(0, peerStart)
    // patch_hash is NOT peer-hash noise: a patch-package edit changes real
    // native content, and normalizing it away made a patched module compare
    // equal to the store build's unpatched one - the exact drift class this
    // tool exists to block. Keep it in the identity so it diffs.
    const patch = segment.match(/_patch_hash=[^_/]+/)
    if (patch && !base.includes('_patch_hash=')) base += patch[0]
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
      // Fail loudly, never blind: defaulting a missing body to '' made every
      // contents source compare equal on both sides if the CLI ever stopped
      // embedding bodies - config changes would sail through unseen.
      if (source.contents == null) {
        throw new Error(
          `fingerprint source ${source.id ?? source.filePath ?? '<unknown>'} ` +
            'has no contents - refusing to compare blind',
        )
      }
      return stripPnpmPeerHashes(source.contents)
    case 'dir':
      // Only pnpm's peer-hash store dirs are digest-blanked: their content
      // hashes churn on rename-only changes (pure noise). Every OTHER dir -
      // a checked-in android/ project, a patch-package edit inside a native
      // module - must compare by hash; blanking all dirs let in-place native
      // edits pass preflight as "native layer matches".
      return (source.filePath ?? '').includes('.pnpm/')
        ? ''
        : (source.hash ?? '')
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
