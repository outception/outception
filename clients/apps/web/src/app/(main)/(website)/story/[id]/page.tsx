import LandingLayout from '@/components/Landing/LandingLayout'
import { StoryPage } from '@/components/Story/StoryPage'
import type { Metadata } from 'next'
import { notFound } from 'next/navigation'

const STORY_ID = /^[a-z0-9][a-z0-9_.:-]{0,127}$/i

export const metadata: Metadata = {
  title: 'Story',
  robots: { index: false, follow: true },
}

export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  if (!STORY_ID.test(id)) notFound()
  return (
    <LandingLayout>
      <StoryPage id={id} />
    </LandingLayout>
  )
}
