import DashboardLayout from '@/components/Layout/DashboardLayout'
import { SidebarProvider } from '@outception-com/ui/components/ui/sidebar'
import { cookies } from 'next/headers'

export default async function Layout({
  children,
}: {
  children: React.ReactNode
}) {
  const cookieStore = await cookies()
  // Collapsed (icon rail) by default; only open if the user explicitly expanded it.
  const defaultOpen = cookieStore.get('sidebar_state')?.value === 'true'

  return (
    <SidebarProvider defaultOpen={defaultOpen}>
      <DashboardLayout>{children}</DashboardLayout>
    </SidebarProvider>
  )
}
