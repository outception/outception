'use client'

import { useEffect, useState, useSyncExternalStore } from 'react'

interface UseIsMobileReturn {
  isMobile: boolean
  isLoading: boolean
}

const useIsMobile = (): UseIsMobileReturn => {
  const [isMobile, setIsMobile] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const checkIsMobile = () => {
      // Check using media query
      const mediaQuery = window.matchMedia('(max-width: 768px)')

      // Check using user agent (additional detection)
      const userAgent = navigator.userAgent.toLowerCase()
      const mobileKeywords = [
        'android',
        'webos',
        'iphone',
        'ipad',
        'ipod',
        'blackberry',
        'windows phone',
        'mobile',
      ]

      const isMobileUA = mobileKeywords.some((keyword) =>
        userAgent.includes(keyword),
      )

      // Combine both checks - prioritize media query but consider user agent
      const isMobileDevice =
        mediaQuery.matches || (isMobileUA && window.innerWidth <= 768)

      setIsMobile(isMobileDevice)
      setIsLoading(false)
    }

    // Initial check
    checkIsMobile()

    // Listen for media query changes
    const mediaQuery = window.matchMedia('(max-width: 768px)')
    const handleChange = () => checkIsMobile()

    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', handleChange)
    } else {
      // Fallback for older browsers
      mediaQuery.addListener(handleChange)
    }

    // Listen for window resize
    window.addEventListener('resize', checkIsMobile)

    return () => {
      if (mediaQuery.removeEventListener) {
        mediaQuery.removeEventListener('change', handleChange)
      } else {
        mediaQuery.removeListener(handleChange)
      }
      window.removeEventListener('resize', checkIsMobile)
    }
  }, [])

  return {
    isMobile,
    isLoading,
  }
}

export default useIsMobile

const MOBILE_QUERY = '(max-width: 768px)'
const subscribeMobile = (onChange: () => void) => {
  const mq = window.matchMedia(MOBILE_QUERY)
  mq.addEventListener('change', onChange)
  return () => mq.removeEventListener('change', onChange)
}
const getMobileSnapshot = () => window.matchMedia(MOBILE_QUERY).matches
const getMobileServerSnapshot = () => false

/** Viewport-only mobile flag, read synchronously from matchMedia: no
 * post-mount state flip (so layout that depends on it doesn't jump on first
 * paint) and a single listener however many components share it. */
export const useIsMobileMedia = (): boolean =>
  useSyncExternalStore(
    subscribeMobile,
    getMobileSnapshot,
    getMobileServerSnapshot,
  )
