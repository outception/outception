'use client'

import { CONFIG } from '@/utils/config'
import { runWhenIdle } from '@/utils/idle'
import { useEffect } from 'react'

// Paths only: a query string can carry a reader's email (the sign-in code
// page) or a sign-in's state, and the counter needs neither. Every URL-ish
// property on an event, and on the person properties it may set, keeps its
// origin and path and loses the rest.
const URLISH = /url|referr/i
const pathOnly = (value: unknown): unknown => {
  if (typeof value !== 'string') return value
  try {
    const url = new URL(value)
    return `${url.origin}${url.pathname}`
  } catch {
    return value
  }
}
const scrub = (properties: Record<string, unknown> | undefined) => {
  if (!properties) return
  for (const key of Object.keys(properties)) {
    if (URLISH.test(key)) properties[key] = pathOnly(properties[key])
  }
}

// Loaded only once the main thread idles, and through a dynamic import, so
// the client's parse and first network calls never sit inside the wall's
// first paint and its code never counts against the route's script budget.
// Memory persistence and no bootstrap: nothing ties one visit to the next,
// which is what "no tracking profile" means in practice. The same-origin
// /ingest path is the proxy in app/ingest, which forwards without our
// cookies.
const init = async () => {
  if (!CONFIG.COUNTER_TOKEN) return
  const { default: posthog } = await import('posthog-js')
  if (posthog.__loaded) return
  posthog.init(CONFIG.COUNTER_TOKEN, {
    ui_host: 'https://eu.i.posthog.com',
    api_host: '/ingest',
    defaults: '2025-05-24',
    persistence: 'memory',
    // A page view per visit and nothing more: no click capture, no
    // heatmaps, no extensions loaded from the vendor, no recordings.
    autocapture: false,
    capture_heatmaps: false,
    capture_dead_clicks: false,
    disable_external_dependency_loading: true,
    advanced_disable_flags: true,
    disable_surveys: true,
    disable_session_recording: true,
    mask_personal_data_properties: true,
    custom_personal_data_properties: ['email', 'token', 'code', 'state'],
    before_send: (event) => {
      if (!event) return event
      scrub(event.properties)
      scrub(event.$set)
      scrub(event.$set_once)
      return event
    },
  })
}

/** The product-analytics counter: a page view per visit, cookieless. */
export function VisitCounter() {
  useEffect(
    () =>
      runWhenIdle(() => {
        void init()
      }),
    [],
  )
  return null
}
