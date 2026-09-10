/** Squarified treemap layout (Bruls, Huizing & van Wijk): lays weighted tiles
 * into a rectangle keeping aspect ratios near 1 so labels stay readable.
 * Pure math shared by the heatmap card; mirrors the web util of the same name. */

export interface TreemapRect {
  x: number
  y: number
  width: number
  height: number
}

/** Positions for `weights` (descending order recommended) inside a
 * `width` × `height` box. Returns one rect per weight, same order. */
export const squarify = (
  weights: number[],
  width: number,
  height: number,
): TreemapRect[] => {
  // Sanitize first: a non-finite or non-positive weight would produce NaN
  // rects (0/0 in `worst`/`layoutRow`) that slip past `<= 1` render guards and
  // crash RN's native layout. Treat them as zero-area tiles.
  const safe = weights.map((w) => (Number.isFinite(w) && w > 0 ? w : 0))
  const total = safe.reduce((sum, w) => sum + w, 0)
  if (total <= 0 || width <= 0 || height <= 0) {
    return weights.map(() => ({ x: 0, y: 0, width: 0, height: 0 }))
  }
  // Scale weights so their sum equals the box area.
  const scaled = safe.map((w) => (w / total) * width * height)
  const rects: TreemapRect[] = []
  let x = 0
  let y = 0
  let w = width
  let h = height
  let row: number[] = []
  let index = 0

  const worst = (candidate: number[], side: number): number => {
    const sum = candidate.reduce((s, v) => s + v, 0)
    const max = Math.max(...candidate)
    const min = Math.min(...candidate)
    const sideSq = side * side
    const sumSq = sum * sum
    return Math.max((sideSq * max) / sumSq, sumSq / (sideSq * min))
  }

  const layoutRow = (finalRow: number[]) => {
    const sum = finalRow.reduce((s, v) => s + v, 0)
    const horizontal = w < h // lay the row along the SHORTER side
    const thickness = sum / (horizontal ? w : h)
    let offset = 0
    for (const area of finalRow) {
      const length = area / thickness
      rects.push(
        horizontal
          ? { x: x + offset, y, width: length, height: thickness }
          : { x, y: y + offset, width: thickness, height: length },
      )
      offset += length
    }
    if (horizontal) {
      y += thickness
      h -= thickness
    } else {
      x += thickness
      w -= thickness
    }
  }

  while (index < scaled.length) {
    const area = scaled[index]
    const side = Math.min(w, h)
    if (row.length === 0 || worst([...row, area], side) <= worst(row, side)) {
      row.push(area)
      index += 1
    } else {
      layoutRow(row)
      row = []
    }
  }
  if (row.length > 0) layoutRow(row)
  return rects
}
