import { createServerSideAPI } from '@/utils/client'
import { handleUpload, type HandleUploadBody } from '@vercel/blob/client'
import { cookies, headers } from 'next/headers'
import { NextResponse } from 'next/server'

// Resolve the caller from the backend-validated session cookie — NOT from the
// `x-outception-user` request header. This route lives under `/api`, which the
// auth middleware (proxy.ts) deliberately excludes from its matcher, so that
// header is never stripped/re-set here and a client could forge it. Validating
// the session directly against the backend closes that impersonation gap.
const getSessionUser = async () => {
  const api = await createServerSideAPI(await headers(), await cookies())
  const { data, response } = await api.GET('/v1/users/me', {
    cache: 'no-cache',
  })
  return response.ok ? data : undefined
}

export async function POST(request: Request): Promise<NextResponse> {
  const body = (await request.json()) as HandleUploadBody

  try {
    const jsonResponse = await handleUpload({
      body,
      request,
      onBeforeGenerateToken: async () => {
        const user = await getSessionUser()
        if (!user) {
          throw new Error('Unauthenticated')
        }

        return {
          allowedContentTypes: ['image/jpeg', 'image/png', 'image/gif'],
          // Randomise the stored key: the raw client filename (e.g. avatar.png)
          // would otherwise collide across users and produce guessable public
          // URLs. Cap the size server-side (the client accept="image/*" is
          // trivially bypassed by calling this route directly).
          addRandomSuffix: true,
          maximumSizeInBytes: 5 * 1024 * 1024,
          tokenPayload: JSON.stringify({ user_id: user.id }),
        }
      },
      onUploadCompleted: async () => {
        // The client receives the blob URL and persists it through the OAuth
        // client form; no server-side bookkeeping is needed here.
      },
    })

    return NextResponse.json(jsonResponse)
  } catch (error) {
    return NextResponse.json(
      { error: (error as Error).message },
      { status: 400 }, // The webhook will retry 5 times waiting for a 200
    )
  }
}
