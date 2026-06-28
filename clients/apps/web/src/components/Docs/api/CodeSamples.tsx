'use client'

import { Box } from '@outception-com/orbit/Box'
import { Check, Copy } from 'lucide-react'
import { useState } from 'react'

export interface RenderedSample {
  label: string
  html: string
  code: string
}

export function CodeSamples({ samples }: { samples: RenderedSample[] }) {
  const [active, setActive] = useState(0)
  const [copied, setCopied] = useState(false)

  if (samples.length === 0) return null
  const current = samples[active]

  const copy = () => {
    void navigator.clipboard.writeText(current.code)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <Box
      flexDirection="column"
      borderWidth={1}
      borderStyle="solid"
      borderColor="border-primary"
      borderRadius="l"
      overflow="hidden"
    >
      <Box
        as="nav"
        alignItems="center"
        borderBottomWidth={1}
        borderStyle="solid"
        borderColor="border-primary"
        backgroundColor="background-secondary"
        paddingHorizontal="s"
      >
        <Box columnGap="xs" flexGrow={1} overflowX="auto">
          {samples.map((sample, index) => (
            <Box
              as="label"
              key={sample.label}
              role="button"
              onClick={() => setActive(index)}
              paddingHorizontal="m"
              paddingVertical="s"
              cursor="pointer"
              borderBottomWidth={2}
              borderStyle="solid"
              borderColor={index === active ? 'border-primary' : 'border-secondary'}
              color={index === active ? 'text-primary' : 'text-secondary'}
              className="text-sm whitespace-nowrap"
            >
              {sample.label}
            </Box>
          ))}
        </Box>
        <Box
          as="label"
          role="button"
          onClick={copy}
          alignItems="center"
          justifyContent="center"
          padding="s"
          cursor="pointer"
          color={{ base: 'text-secondary', hover: 'text-primary' }}
          aria-label="Copy code"
        >
          {copied ? <Check size={16} /> : <Copy size={16} />}
        </Box>
      </Box>
      <Box
        overflowX="auto"
        className="[&>pre]:my-0 [&>pre]:rounded-none [&>pre]:border-none [&>pre]:p-4"
        dangerouslySetInnerHTML={{ __html: current.html }}
      />
    </Box>
  )
}
