import { buildSearchIndex } from '@/lib/docs/search'

// Not force-static: the handbook is auth-gated by the proxy middleware, so this
// index is built per request behind the session check rather than baked public.
export const dynamic = 'force-dynamic'

export async function GET() {
  return Response.json(await buildSearchIndex('handbook'))
}
