'use client'

import { getClientCountry } from '@/utils/i18n/shared'
import { weatherApi, type WeatherLocation } from '@/utils/weather'
import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { defaultRetry } from './retry'

/** Resolve the reader's location for weather: precise geolocation when the
 * browser grants it, otherwise the IP country. Returns null while unresolved
 * (during the permission prompt) AND when there's no signal at all — no precise
 * location and no IP country — so the query stays disabled instead of fetching a
 * default city. */
const useWeatherLocation = (): WeatherLocation | null => {
  const [location, setLocation] = useState<WeatherLocation | null>(null)

  useEffect(() => {
    let cancelled = false
    const fallback = () => {
      if (cancelled) return
      // Precise location was denied/unavailable: fall back to the IP country
      // (the geo cookie the proxy sets from Cloudflare). With neither there's no
      // location signal at all — keep the query disabled (the card shows
      // "unavailable") rather than fetching a default city.
      const country = getClientCountry()
      setLocation(country ? { country } : null)
    }
    if (typeof navigator === 'undefined' || !navigator.geolocation) {
      fallback()
      return
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        if (!cancelled) {
          setLocation({
            latitude: pos.coords.latitude,
            longitude: pos.coords.longitude,
          })
        }
      },
      fallback,
      { timeout: 8000, maximumAge: 15 * 60_000 },
    )
    return () => {
      cancelled = true
    }
  }, [])

  return location
}

export const useWeather = () => {
  const location = useWeatherLocation()
  return useQuery({
    queryKey: ['news', 'weather', location],
    queryFn: () => weatherApi.forecast(location as WeatherLocation),
    enabled: location !== null,
    staleTime: 15 * 60_000,
    retry: defaultRetry,
  })
}
