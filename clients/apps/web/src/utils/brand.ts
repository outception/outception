import { DEFAULT_WALL_THEME } from './wallTheme'

/**
 * The default edition's light install color for the one place that needs a
 * literal color outside CSS and can't be tone-aware: the PWA manifest's
 * static `background_color` / `theme_color` (the install splash and OS
 * task-switcher tint, which a light-first install shows). Derived from the
 * default edition's chrome in WALL_THEMES so it can't drift from the app.
 * The live, tone-aware status-bar chrome is handled elsewhere — the
 * pre-hydration script and ThemeColorMeta read the same per-tone values.
 */
export const PAPER_COLOR = DEFAULT_WALL_THEME.chrome.light
