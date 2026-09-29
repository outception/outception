import { Box } from '@/components/Shared/Box'
import { Image as ExpoImage, ImageLoadEventData, ImageProps } from 'expo-image'
import { LayoutChangeEvent } from 'react-native'
import { Text } from '../Text'
import { useImageSizeWarning } from './hooks/useImageSizeWarning'

export const Image = ({
  onLoad,
  onLayout,
  style,
  source,
  ...props
}: ImageProps) => {
  const {
    sizeWarning,
    onLayout: onSizeWarningLayout,
    onImageLoad,
  } = useImageSizeWarning(source)

  const handleLoad = (event: ImageLoadEventData) => {
    if (__DEV__) onImageLoad(event.source.width)
    onLoad?.(event)
  }

  const handleLayout = (event: LayoutChangeEvent) => {
    if (__DEV__) onSizeWarningLayout(event)
    onLayout?.(event)
  }

  const showWarning = __DEV__ && sizeWarning

  return (
    <>
      <ExpoImage
        {...props}
        source={source}
        style={style}
        onLayout={handleLayout}
        onLoad={handleLoad}
      />
      {showWarning ? (
        <Box
          backgroundColor="error"
          justifyContent="center"
          alignItems="center"
          opacity={0.8}
          style={{
            position: 'absolute',
            top: sizeWarning.frame.y,
            left: sizeWarning.frame.x,
            width: sizeWarning.frame.width,
            height: sizeWarning.frame.height,
            zIndex: 999,
          }}
        >
          <Text textAlign="center" style={{ fontSize: 9, lineHeight: 10 }}>
            Image is{' '}
            {sizeWarning.type === 'large'
              ? `${Math.round((sizeWarning.actual / sizeWarning.target) * 100) - 100}% too large`
              : `${100 - Math.round((sizeWarning.actual / sizeWarning.target) * 100)}% too small`}
          </Text>
        </Box>
      ) : null}
    </>
  )
}
