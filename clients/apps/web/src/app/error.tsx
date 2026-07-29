'use client'

import InternalServerError from '@/components/Shared/InternalServerError'
import * as Sentry from '@sentry/nextjs'
import { useEffect } from 'react'

export default function Error({ error }: { error: Error }) {
  useEffect(() => {
    Sentry.captureException(error)
  }, [error])

  // No <html>/<body> here — this boundary renders INSIDE the root layout's
  // body. Only global-error.tsx owns the document. Nesting them produces a
  // hydration mismatch on the one page that most needs to render.
  return (
    <InternalServerError
      digest={'digest' in error ? (error.digest as string) : undefined}
    />
  )
}
