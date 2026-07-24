/** The app's single static backdrop — a sheet of newsprint. A flat cream wash
 * with the faintest warm vignette in light ("day edition"), near-black warm
 * neutrals in dark ("night edition"). Purely static CSS: no canvas, no
 * animation — the paper grain (body::after in globals.css) supplies the
 * texture. Theming comes from the `.dark` class, which next-themes sets before
 * first paint, so there is never a flash. pointer-events-none so it never
 * intercepts input. */
export const PaperBackground = () => {
  return (
    <div
      aria-hidden
      // .paper-page (globals.css) carries both editions from the newsprint
      // tokens: flat FT salmon by day, the near-black vignette by night.
      className="paper-page pointer-events-none fixed inset-0 -z-10 overflow-hidden"
    />
  )
}
