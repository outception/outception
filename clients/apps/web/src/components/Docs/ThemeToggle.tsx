'use client'

import { Box } from '@outception-com/orbit/Box'
import { Moon, Sun } from 'lucide-react'
import { useTheme } from 'next-themes'
import { useEffect, useState } from 'react'

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme()
  const [mounted, setMounted] = useState(false)
  useEffect(() => setMounted(true), [])

  const isDark = resolvedTheme === 'dark'
  return (
    <Box
      as="label"
      role="button"
      aria-label="Toggle theme"
      onClick={() => setTheme(isDark ? 'light' : 'dark')}
      alignItems="center"
      justifyContent="center"
      width={36}
      height={36}
      borderRadius="m"
      cursor="pointer"
      color={{ base: 'text-secondary', hover: 'text-primary' }}
      backgroundColor={{ hover: 'background-secondary' }}
    >
      {mounted && isDark ? <Sun size={18} /> : <Moon size={18} />}
    </Box>
  )
}
