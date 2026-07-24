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
