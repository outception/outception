import { Text } from '@/components/Shared/Text'
import type { SupportedLocale } from '@outception-com/i18n'
import type { ReactElement } from 'react'
import Svg, { Circle, G, Path, Rect } from 'react-native-svg'

// Custom inline flags for stateless / sub-national languages that have no ISO
// country of their own, so there's no flag emoji for them (the picker uses emoji
// everywhere else). Mirrors the web Flag.tsx renditions. Drawn at a 3:2 ratio.

const IkurrinaFlag = (w: number): ReactElement => (
  <Svg width={w} height={(w * 2) / 3} viewBox="0 0 30 20">
    <Rect width="30" height="20" fill="#D52B1E" />
    <Path d="M0 0 30 20M30 0 0 20" stroke="#009B48" strokeWidth={3.2} />
    <Rect x="13" width="4" height="20" fill="#fff" />
    <Rect y="8" width="30" height="4" fill="#fff" />
  </Svg>
)

const SenyeraFlag = (w: number): ReactElement => (
  <Svg width={w} height={(w * 2) / 3} viewBox="0 0 27 18">
    <Rect width="27" height="18" fill="#FCDD09" />
    <Rect y="2" width="27" height="2" fill="#DA121A" />
    <Rect y="6" width="27" height="2" fill="#DA121A" />
    <Rect y="10" width="27" height="2" fill="#DA121A" />
    <Rect y="14" width="27" height="2" fill="#DA121A" />
  </Svg>
)

const FourProvincesFlag = (w: number): ReactElement => (
  <Svg width={w} height={(w * 2) / 3} viewBox="0 0 30 20">
    {/* Leinster - green field, gold harp */}
    <Rect width="15" height="10" fill="#169B62" />
    <G fill="#F4C430">
      <Path d="M6 2.4c2.6.4 2.6 4 .9 5.2h-1c1.3-1 1.4-3.9-.7-4.2z" />
      <Rect x="5.7" y="2.4" width="0.7" height="5.2" />
    </G>
    {/* Connacht - white with eagle, blue with an armed arm */}
    <Rect x="15" width="7.5" height="10" fill="#fff" />
    <Rect x="22.5" width="7.5" height="10" fill="#003F87" />
    <Path d="M18.7 2.6 20 5l-1.3 2.4L17.4 5z" fill="#111" />
    <G fill="#F4C430">
      <Rect x="25.9" y="3" width="0.8" height="4.2" />
      <Path d="M25.4 3.2h1.9l-.95-1.4z" />
    </G>
    {/* Munster - blue field, three gold crowns */}
    <Rect y="10" width="15" height="10" fill="#003F87" />
    <G fill="#F4C430">
      <Path d="M6.1 12h2.8l-.3 1.1H6.4zM6.1 12l.55-.8.55.8.35-.8.35.8.55-.8.55.8z" />
      <Path d="M4.2 14.4h2.4l-.28 1H4.48zM4.2 14.4l.5-.7.5.7.3-.7.3.7.5-.7.5.7z" />
      <Path d="M8.4 14.4h2.4l-.28 1H8.68zM8.4 14.4l.5-.7.5.7.3-.7.3.7.5-.7.5.7z" />
    </G>
    {/* Ulster - gold field, red cross and the red hand on a white shield */}
    <Rect x="15" y="10" width="15" height="10" fill="#FFCC00" />
    <Rect x="21.8" y="10" width="1.4" height="10" fill="#CE1126" />
    <Rect x="15" y="14.3" width="15" height="1.4" fill="#CE1126" />
    <Circle cx="22.5" cy="15" r="2.6" fill="#fff" />
    <Path
      d="M22.5 13.1v3.6M21.3 13.6v2.9M23.7 13.6v2.9M22 13.4v3.2M23 13.4v3.2"
      stroke="#CE1126"
      strokeWidth={0.55}
      strokeLinecap="round"
    />
  </Svg>
)

const CUSTOM: Partial<Record<SupportedLocale, (w: number) => ReactElement>> = {
  eu: IkurrinaFlag,
  ca: SenyeraFlag,
  ga: FourProvincesFlag,
}

/** A language flag: the emoji for national languages, a custom inline SVG for
 * stateless/sub-national ones (Basque, Catalan, Irish) that have no flag emoji.
 * Mirrors the web flag picker. */
export const LocaleFlag = ({
  locale,
  emoji,
  size = 20,
}: {
  locale?: SupportedLocale
  emoji: string
  size?: number
}) => {
  const custom = locale ? CUSTOM[locale] : undefined
  if (custom) return custom(size)
  return <Text variant="body">{emoji}</Text>
}
