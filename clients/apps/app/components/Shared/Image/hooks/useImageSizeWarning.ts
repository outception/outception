import { ImageProps } from 'expo-image'
import { useCallback, useEffect, useRef, useState } from 'react'
import { LayoutChangeEvent, PixelRatio } from 'react-native'

const LARGE_IMAGE_THRESHOLD_PERCENTAGE = 400
const SMALL_IMAGE_THRESHOLD_PERCENTAGE = 90

interface ImageFrame {
  x: number
  y: number
  width: number
  height: number
}

interface SizeWarning {
  type: 'large' | 'small'
  target: number
  actual: number
  frame: ImageFrame
}

interface UseImageSizeWarningReturn {
  sizeWarning: SizeWarning | null
  onLayout: (event: LayoutChangeEvent) => void
  onImageLoad: (width: number) => void
}

const isSameWarning = (a: SizeWarning | null, b: SizeWarning | null) => {
  if (a === b) return true
  if (!a || !b) return false
  return (
    a.type === b.type &&
    a.target === b.target &&
    a.actual === b.actual &&
    a.frame.x === b.frame.x &&
    a.frame.y === b.frame.y &&
    a.frame.width === b.frame.width &&
    a.frame.height === b.frame.height
  )
}

export const useImageSizeWarning = (
  source: ImageProps['source'],
): UseImageSizeWarningReturn => {
  const [sizeWarning, setSizeWarning] = useState<SizeWarning | null>(null)

  const frame = useRef<ImageFrame | null>(null)
  const sourceWidth = useRef(0)

  const sourceKey = __DEV__ ? JSON.stringify(source ?? null) : ''

  useEffect(() => {
    sourceWidth.current = 0
    setSizeWarning(null)
  }, [sourceKey])

  const checkForSizeWarning = useCallback(() => {
    if (!frame.current?.width || !sourceWidth.current) {
      return
    }

    const targetWidth = PixelRatio.getPixelSizeForLayoutSize(
      Math.round(frame.current.width),
    )

    const percentage = Math.round((sourceWidth.current / targetWidth) * 100)

    let next: SizeWarning | null = null
    if (percentage > LARGE_IMAGE_THRESHOLD_PERCENTAGE) {
      next = {
        type: 'large',
        target: targetWidth,
        actual: sourceWidth.current,
        frame: frame.current,
      }
    } else if (percentage < SMALL_IMAGE_THRESHOLD_PERCENTAGE) {
      next = {
        type: 'small',
        target: targetWidth,
        actual: sourceWidth.current,
        frame: frame.current,
      }
    }
    setSizeWarning((current) => (isSameWarning(current, next) ? current : next))
  }, [])

  const onLayout = useCallback(
    (event: LayoutChangeEvent) => {
      const { x, y, width, height } = event.nativeEvent.layout
      frame.current = { x, y, width, height }
      checkForSizeWarning()
    },
    [checkForSizeWarning],
  )

  const onImageLoad = useCallback(
    (width: number) => {
      sourceWidth.current = width
      checkForSizeWarning()
    },
    [checkForSizeWarning],
  )

  return {
    sizeWarning,
    onLayout,
    onImageLoad,
  }
}
