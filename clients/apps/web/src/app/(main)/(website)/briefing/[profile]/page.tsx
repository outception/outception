import { BriefingPage } from '@/components/Briefing/BriefingPage'
import LandingLayout from '@/components/Landing/LandingLayout'
import type { Metadata } from 'next'
import { notFound } from 'next/navigation'

const PROFILE_ID = /^[a-z0-9-]{1,40}$/

export async function generateMetadata({
  params,
}: {
  params: Promise<{ profile: string }>
}): Promise<Metadata> {
  const { profile } = await params
  return { title: `Briefing: ${profile}` }
}

export default async function Page({
  params,
}: {
  params: Promise<{ profile: string }>
}) {
  const { profile } = await params
  if (!PROFILE_ID.test(profile)) notFound()
  return (
    <LandingLayout>
      <BriefingPage profile={profile} />
    </LandingLayout>
  )
}
