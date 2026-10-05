import { describe, expect, it } from 'vitest'
import { parseChangelog } from './ChangelogPage'

describe('parseChangelog', () => {
  it('reads releases, their notes and their lines', () => {
    const releases = parseChangelog(
      '# Title\n\nIntro.\n\n## 1.0\n\nA note.\n- one\n- two\n\n## 0.9\n- three\n',
    )
    expect(releases).toEqual([
      { heading: '1.0', notes: ['A note.'], lines: ['one', 'two'] },
      { heading: '0.9', notes: [], lines: ['three'] },
    ])
  })
})
