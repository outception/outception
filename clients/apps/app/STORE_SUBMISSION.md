# Store Submission — Outception mobile

Everything needed to ship the Expo app to the **App Store** and **Google Play**.
Config is already store-ready; the rest is account setup + assets you provide.

## Already in place (code/config)

- Bundle IDs: iOS `com.outception.Outception`, Android `com.outception.Outception`
- Version `1.5.0`; production build numbers auto-increment (`eas.json` production profile)
- App icon / adaptive icon / splash assets present (`assets/images/`)
- iOS ATT prompt + AdMob app IDs wired (validated against a real prebuild)
- `ITSAppUsesNonExemptEncryption: false` (no export-compliance questionnaire)
- **No** location/camera/mic/contacts permissions requested (weather uses IP) → fewer review flags
- Privacy Policy live + linked: `https://outception.com/privacy`

## Prerequisites (you)

- **Apple Developer Program** — already have it (team `55U3YA3QTA`).
- **Google Play Console** — one-time **$25** account at play.google.com/console.
- EAS is configured (owner `outception-app`, project id in `app.config.js`).

## 1. Create the app records

- **App Store Connect** → Apps → **+** → New App (iOS): Name `Outception`, bundle
  `com.outception.Outception`, an SKU, primary language English. Note the numeric
  **Apple ID (ascAppId)** it assigns — used by `eas submit`.
- **Play Console** → **Create app**: Name `Outception`, App, Free, accept declarations.

## 2. Build

```bash
cd clients/apps/app
eas login                                          # owner: outception-app
eas build --profile production --platform all      # iOS .ipa + Android .aab
```

(First build sets up credentials: Android auto-generates a keystore; iOS uses your Apple account for signing.)

## 3. Submit

```bash
eas submit --profile production --platform ios      # prompts for Apple ID + ascAppId
eas submit --profile production --platform android  # needs a Play service-account JSON key
```

- `eas.json` already sets the Apple team id and Android `internal` track.
- Android: create a **service account** in Play Console → API access, download its JSON, pass with `--key path/to/key.json` (or set it in `eas.json`).

## 4. Store listing content (paste into the consoles)

- **Name:** Outception
- **Subtitle (iOS, ≤30):** A live wall of world news
- **Short description (Play, ≤80):** A live wall of headlines from 250+ sources, across every topic.
- **Full description:**
  > Outception is a live wall of the world's headlines. Follow 250+ news sources
  > across every topic — world, tech, business, sport, science, and more — on one
  > fast, swipeable deck. Tap any headline to read the full story at the source.
  >
  > • A swipe-through deck of live headlines, updated continuously
  > • 250+ sources you can follow, filter by topic, and search
  > • Local weather at a glance
  > • Clean, distraction-free reading — no account required
  >
  > Free, ad-supported.
- **Keywords (iOS, ≤100):** news,headlines,world news,breaking,feed,wall,sources,weather,tech,sport
- **Category:** News
- **Support URL:** https://outception.com · **Marketing URL:** https://outception.com
- **Privacy Policy URL:** https://outception.com/privacy

## 5. App Privacy (App Store) / Data safety (Play) — answers

Accurate to what the mobile app collects:

| Data                        | Collected                 | Purpose                         | Linked to you | Used to track          |
| --------------------------- | ------------------------- | ------------------------------- | ------------- | ---------------------- |
| Email address               | Yes (only if you sign in) | App functionality, Account      | Yes           | No                     |
| User/Account ID             | Yes (if signed in)        | App functionality               | Yes           | No                     |
| Advertising ID / Device ID  | Yes                       | Advertising (AdMob)             | No            | **Yes** (gated by ATT) |
| Product interaction (usage) | Yes                       | Analytics                       | No            | No                     |
| Crash + performance data    | Yes                       | App functionality (diagnostics) | No            | No                     |
| Coarse location (from IP)   | Yes                       | App functionality (weather)     | No            | No                     |

- **Does the app track?** Yes — advertising identifiers via AdMob, only after the ATT prompt is allowed.
- **Is data sold?** No.
- Third parties: Google (AdMob), plus analytics/diagnostics processors (PostHog, Sentry).

## 6. Assets you provide

- **App icon 1024×1024** (from `assets/images/icon.png`).
- **iOS screenshots:** iPhone 6.7"/6.9" (required). iPad not needed (`supportsTablet: false`).
- **Android:** phone screenshots + a **1024×500 feature graphic**.

## 7. Review gotchas

- **ATT prompt must appear** on iOS (wired — don't remove it).
- **Content:** keep it headlines + link-out; don't start reproducing full third-party articles.
- **"Minimum functionality":** a native news reader clears Apple's bar (it's not a repackaged website).
- **Age rating:** fill the content questionnaire — a news app with unrestricted topics typically lands 12+/Teen.
- After the app is **published**, link its store listing back in **AdMob → your app → App settings** (helps verification + reduces invalid traffic).
  </content>
