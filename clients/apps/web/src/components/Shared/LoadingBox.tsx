import { Box, type BoxProps } from '@outception-com/orbit/Box'

export const LoadingBox = (props: BoxProps) => (
  <Box
    display="block"
    {...props}
    // eslint-disable-next-line outception/no-classname-box
    className="dark:bg-outception-700 animate-pulse bg-gray-100"
  />
)
