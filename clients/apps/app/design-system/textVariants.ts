import { ColorToken } from '@/design-system/theme'

type TextVariant = {
  color?: ColorToken
  fontSize?: number
  lineHeight?: number
  fontWeight?: '400' | '500' | '600' | '700' | 'bold'
  fontFamily?: string
  textTransform?: 'none' | 'capitalize' | 'uppercase' | 'lowercase'
}

// The Magnific stack, mirrored on native: Geist for text/UI, Hanken
// Grotesk for display. Static per-weight families (not fontWeight) so
// Android renders the intended cut.
export const textVariants = {
  defaults: {
    color: 'text',
    fontSize: 16,
    lineHeight: 22,
    fontFamily: 'Geist_400Regular',
  },
  body: {
    fontSize: 16,
    lineHeight: 22,
    fontFamily: 'Geist_400Regular',
  },
  bodyMedium: {
    fontSize: 16,
    lineHeight: 22,
    fontFamily: 'Geist_500Medium',
  },
  // Body-size headline face (Hanken), mirroring the web wall's `serif` headline
  // rows — the story text renders in the display family, not the Geist UI face.
  // Web's wall sets body headlines in Hanken 400 at 16/24 (`Text variant="body"
  // serif`). This was 500 at 16/22, so every headline read a step heavy.
  bodySerif: {
    fontSize: 16,
    lineHeight: 24,
    fontFamily: 'HankenGrotesk_400Regular',
  },
  // The lead story: web's `heading-xxs` + serif = 18 / 1.375 / 500.
  leadSerif: {
    fontSize: 18,
    lineHeight: 25,
    fontFamily: 'HankenGrotesk_500Medium',
  },
  // The weather card's hero figure: web's `heading-2xl` = 60 / lh 1 / 400.
  weatherTemp: {
    fontSize: 58,
    lineHeight: 60,
    fontFamily: 'HankenGrotesk_400Regular',
  },
  // Web's nav tab: 14px, serif on the active tab.
  navTabActive: {
    fontSize: 14,
    lineHeight: 20,
    fontFamily: 'HankenGrotesk_500Medium',
  },
  bodySmall: {
    fontSize: 14,
    lineHeight: 20,
    fontFamily: 'Geist_400Regular',
  },
  caption: {
    fontSize: 12,
    lineHeight: 16,
    fontFamily: 'Geist_400Regular',
  },
  subtitle: {
    fontSize: 18,
    lineHeight: 26,
    fontFamily: 'Geist_500Medium',
  },
  title: {
    fontSize: 20,
    lineHeight: 28,
    fontFamily: 'HankenGrotesk_700Bold',
  },
  titleLarge: {
    fontSize: 24,
    lineHeight: 32,
    fontFamily: 'HankenGrotesk_800ExtraBold',
  },
  headline: {
    fontSize: 22,
    lineHeight: 30,
    fontFamily: 'HankenGrotesk_700Bold',
  },
  headlineLarge: {
    fontSize: 32,
    lineHeight: 40,
    fontFamily: 'HankenGrotesk_800ExtraBold',
  },
  headlineXLarge: {
    fontSize: 36,
    lineHeight: 48,
    fontFamily: 'HankenGrotesk_800ExtraBold',
  },
  display: {
    fontSize: 58,
    lineHeight: 64,
    fontFamily: 'HankenGrotesk_800ExtraBold',
  },
} satisfies Record<string, TextVariant>

export type TextVariantKey = Exclude<keyof typeof textVariants, 'defaults'>
