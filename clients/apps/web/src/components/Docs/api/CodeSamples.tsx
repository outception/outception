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
              borderColor={
                index === active ? 'border-primary' : 'border-secondary'
              }
              color={index === active ? 'text-primary' : 'text-secondary'}
            >
              <span className="text-sm whitespace-nowrap">{sample.label}</span>
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
      <div className="[&_pre]:my-0 [&_pre]:rounded-none [&_pre]:border-none [&_pre]:p-4">
        <Box
          overflowX="auto"
          dangerouslySetInnerHTML={{ __html: current.html }}
        />
      </div>
    </Box>
  )
}
