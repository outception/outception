// Google Analytics now loads app-wide and consent-gated from the root layout
// (see ConsentedGoogleAnalytics) so it mirrors PostHog for a fair comparison —
// it no longer loads (un-gated) only on the marketing pages.
export default function Layout({ children }: { children: React.ReactNode }) {
  return children
}
