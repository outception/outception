/**
 * Regression tests for the round-trip `prune.ts` performs on every locale file.
 *
 * The prune flattens a locale, drops the keys absent from `en.ts`, and
 * unflattens the rest. Two properties of that round-trip are load-bearing and
 * neither was covered:
 *
 * 1. `flattenKeys` deliberately drops `_mode: 'plural'` markers, and
 *    `unflattenKeys` only restores them for the paths it is handed. An earlier
 *    version of prune.ts omitted that argument. It corrupted nothing at the
 *    time only because `en.ts` happened to contain no plural keys — but the
 *    first plural key added would have stripped the marker from all 46 locales,
 *    and `t()` would then hand a raw object to `.replace()` and throw inside
 *    render for every non-English reader simultaneously.
 *
 * 2. Annotated `{ value, _llmContext }` entries must survive as values, not be
 *    descended into as nested objects.
 */
import { describe, expect, it } from 'vitest'
import { pruneLocaleObject } from './prune'
import {
  type NestedObject,
  findOrphanedKeys,
  flattenKeys,
  flattenKeysToStrings,
} from './utils'

/** Drives the real prune helper, so a regression in prune.ts fails here. */
const pruneLocale = (
  source: NestedObject,
  locale: NestedObject,
): NestedObject => {
  const sourceKeys = flattenKeys(source)
  return pruneLocaleObject(
    sourceKeys,
    locale,
    findOrphanedKeys(sourceKeys, locale),
  )
}

describe('prune round-trip', () => {
  it('preserves the _mode marker on plural entries', () => {
    const en: NestedObject = {
      items: { _mode: 'plural', one: '# item', other: '# items' },
    }
    const fr: NestedObject = {
      items: { _mode: 'plural', one: '# article', other: '# articles' },
      dead: 'supprime-moi',
    }

    const result = pruneLocale(en, fr) as {
      items: Record<string, string>
      dead?: string
    }

    expect(result.items._mode).toBe('plural')
    expect(result.items.one).toBe('# article')
    expect(result.items.other).toBe('# articles')
  })

  it('removes keys absent from the source locale', () => {
    const en: NestedObject = { a: { b: 'keep' } }
    const fr: NestedObject = { a: { b: 'garder', c: 'jeter' }, d: 'jeter' }

    const result = pruneLocale(en, fr) as {
      a: Record<string, string>
      d?: string
    }

    expect(result.a.b).toBe('garder')
    expect(result.a.c).toBeUndefined()
    expect(result.d).toBeUndefined()
  })

  it('keeps every key the source still defines, with values intact', () => {
    const en: NestedObject = {
      nested: { deep: { key: 'x' } },
      top: 'y',
    }
    const fr: NestedObject = {
      nested: { deep: { key: 'profond' } },
      top: 'haut',
      orphan: 'parti',
    }

    const result = pruneLocale(en, fr)

    expect(flattenKeysToStrings(result)).toEqual(
      new Map([
        ['nested.deep.key', 'profond'],
        ['top', 'haut'],
      ]),
    )
  })

  it('treats an annotated {value,_llmContext} source entry as one key', () => {
    // en.ts writes ordinals this way; locales write plain strings. The entry
    // must match as `ordinal.one`, not descend to `ordinal.one.value`, or every
    // locale's ordinals would look orphaned and be deleted.
    const en: NestedObject = {
      ordinal: { one: { value: 'st', _llmContext: 'ordinal suffix' } },
    }
    const fr: NestedObject = { ordinal: { one: 'er' } }

    const result = pruneLocale(en, fr) as { ordinal: Record<string, string> }

    expect(result.ordinal.one).toBe('er')
  })
})
