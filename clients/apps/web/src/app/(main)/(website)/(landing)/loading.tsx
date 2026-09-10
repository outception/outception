import { Box } from '@outception-com/orbit/Box'

/** Shown while the landing route resolves. The layout is `force-dynamic` and
 * the root layout awaits feature flags, so without this the reader stares at a
 * blank tab on a slow connection or a degraded flag service. */
export default function Loading() {
  return (
    <Box
      flexDirection="column"
      alignItems="center"
      justifyContent="center"
      minHeight="60vh"
      rowGap="l"
    >
      <Box
        width="min(680px, 90vw)"
        height={420}
        borderRadius="l"
        backgroundColor="background-card"
        opacity={0.6}
      />
    </Box>
  )
}
