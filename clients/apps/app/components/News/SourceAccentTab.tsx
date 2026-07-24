import { Box } from '@/components/Shared/Box'

/** The source's accent colour as a short rounded tab hanging from a card's
 * top-left edge (matches the web sheet). */
export const SourceAccentTab = ({ color }: { color: string }) => (
  <Box
    position="absolute"
    top={0}
    left={16}
    width={40}
    height={4}
    style={{
      backgroundColor: color,
      borderBottomLeftRadius: 999,
      borderBottomRightRadius: 999,
    }}
  />
)
