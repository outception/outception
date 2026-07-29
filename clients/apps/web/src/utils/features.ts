// Accounts (login + dashboard) are deactivated for the ad-supported launch.
// The auth/dashboard code is kept intact but unreachable — no sign-in entry
// points are shown, and /auth and /dashboard redirect home. Flip this to `true`
// to re-enable accounts (e.g. for cross-device sync or a premium tier).
export const ACCOUNTS_ENABLED = false
