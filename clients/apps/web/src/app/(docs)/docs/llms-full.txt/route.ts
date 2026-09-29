import { buildLlmsFull } from '@/lib/docs/llms'

export const dynamic = 'force-static'

export async function GET() {
  return new Response(await buildLlmsFull('docs'), {
    headers: { 'Content-Type': 'text/plain; charset=utf-8' },
  })
}
