import type { schemas } from '@outception-com/client'

export type RaceRow = schemas['RaceRow']
export type RaceMode = schemas['Race']['mode']
export type RaceSize = 'strip' | 'panel' | 'sheet'

/** The last day in the rows, 'YYYY-MM-DD'; empty when there are none. */
export const lastDate = (rows: readonly RaceRow[]): string =>
  rows.reduce((last, row) => (row.date > last ? row.date : last), '')

/** The rows of the last `days` days, counted back from the last day in
 * the data, so a shorter range still ends on the latest frame. */
export const trimRows = (rows: readonly RaceRow[], days: number): RaceRow[] => {
  const last = lastDate(rows)
  if (!last) return []
  const end = new Date(`${last}T00:00:00Z`)
  const start = new Date(end.getTime() - (days - 1) * 86_400_000)
  const since = start.toISOString().slice(0, 10)
  return rows.filter((row) => row.date >= since)
}

/** One bar in one frame: its name and its value. */
export interface RaceBar {
  name: string
  value: number
}

export interface RaceFrames {
  /** The frames' dates, oldest first. */
  dates: string[]
  /** For each date, the bars on screen, biggest first. */
  frames: RaceBar[][]
  /** Every name that is ever on screen, in order of first appearance: one
   * row each, so a bar keeps its row as it moves and can be animated. */
  names: string[]
}

/** The race, frame by frame. A bar is on screen only with a value above
 * zero (a name joins the race with its first value, so no bar sits at
 * zero) and only among the `topN` biggest. With `cumulative`, each frame
 * carries the running total of the days so far. Frames before the first
 * value are left out. */
export const buildFrames = (
  rows: readonly RaceRow[],
  { cumulative, topN }: { cumulative: boolean; topN: number },
): RaceFrames => {
  const byDate = new Map<string, Map<string, number>>()
  for (const row of rows) {
    const day = byDate.get(row.date) ?? new Map<string, number>()
    day.set(row.name, (day.get(row.name) ?? 0) + row.value)
    byDate.set(row.date, day)
  }
  const totals = new Map<string, number>()
  const dates: string[] = []
  const frames: RaceBar[][] = []
  const names: string[] = []
  const seen = new Set<string>()
  for (const date of [...byDate.keys()].sort()) {
    const day = byDate.get(date)!
    let values: Map<string, number>
    if (cumulative) {
      for (const [name, value] of day)
        totals.set(name, (totals.get(name) ?? 0) + value)
      values = totals
    } else {
      values = day
    }
    const bars = [...values]
      .filter(([, value]) => value > 0)
      .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
      .slice(0, topN)
      .map(([name, value]) => ({ name, value }))
    if (bars.length === 0 && frames.length === 0) continue
    dates.push(date)
    frames.push(bars)
    for (const bar of bars) {
      if (!seen.has(bar.name)) {
        seen.add(bar.name)
        names.push(bar.name)
      }
    }
  }
  return { dates, frames, names }
}
