import { CONFIG } from '@/utils/config'
import { isImpersonating } from '@/utils/impersonation'
import KeyboardArrowDown from '@mui/icons-material/KeyboardArrowDown'
import { schemas } from '@outception-com/client'
import { Avatar } from '@outception-com/orbit'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarTrigger,
  useSidebar,
} from '@outception-com/ui/components/atoms/Sidebar'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@outception-com/ui/components/ui/dropdown-menu'
import { Separator } from '@outception-com/ui/components/ui/separator'
import { motion } from 'motion/react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { twMerge } from 'tailwind-merge'
import LogoIcon from '@/components/Brand/logos/LogoIcon'
import {
  AccountNavigation,
  OrganizationNavigation,
} from './DashboardNavigation'

export const DashboardSidebar = ({
  type = 'organization',
  organization,
  organizations,
}: {
  type?: 'organization' | 'account'
  organization?: schemas['Organization']
  organizations: schemas['Organization'][]
}) => {
  const router = useRouter()
  const { state } = useSidebar()

  const isCollapsed = state === 'collapsed'

  const navigateToOrganization = (org: schemas['Organization']) => {
    router.push(`/dashboard/${org.slug}`)
  }

  const [_isImpersonating, setIsImpersonating] = useState(false)
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- client-only cookie read to avoid hydration mismatch
    setIsImpersonating(isImpersonating())
  }, [])
  const isTopBannerVisible = CONFIG.IS_SANDBOX || _isImpersonating

  return (
    <Sidebar variant="inset" collapsible="icon">
      <SidebarHeader
        className={twMerge(
          'flex md:pt-3.5',
          isTopBannerVisible ? 'md:pt-10' : '',
          isCollapsed
            ? 'flex-row items-center justify-between gap-y-4 md:flex-col md:items-start md:justify-start'
            : 'flex-row items-center justify-between',
        )}
      >
        <Link
          href={organization ? `/dashboard/${organization.slug}` : '/dashboard'}
        >
          <LogoIcon size={32} className="text-black dark:text-white" />
        </Link>
        <motion.div
          key={isCollapsed ? 'header-collapsed' : 'header-expanded'}
          className={`flex ${isCollapsed ? 'flex-row md:flex-col-reverse' : 'flex-row'} items-center gap-2`}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1 }}
        >
          <SidebarTrigger />
        </motion.div>
      </SidebarHeader>

      <SidebarContent className="gap-4 px-2 py-4">
        <motion.div
          key={isCollapsed ? 'nav-collapsed' : 'nav-expanded'}
          className="flex flex-col items-center gap-2"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1 }}
        >
          {type === 'account' && <AccountNavigation />}
          {type === 'organization' && organization && (
            <OrganizationNavigation organization={organization} />
          )}
        </motion.div>
      </SidebarContent>
      <SidebarFooter>
        <Separator />
        {type === 'organization' && organization && (
          <SidebarMenu>
            <SidebarMenuItem>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <SidebarMenuButton>
                    <Avatar
                      name={organization.name}
                      avatar_url={organization.avatar_url}
                      className="h-6 w-6"
                    />
                    {!isCollapsed && (
                      <>
                        <span className="min-w-0 truncate">
                          {organization.name}
                        </span>
                        <KeyboardArrowDown
                          className="ml-auto"
                          fontSize="small"
                        />
                      </>
                    )}
                  </SidebarMenuButton>
                </DropdownMenuTrigger>
                <DropdownMenuContent
                  side="top"
                  align={isCollapsed ? 'start' : 'center'}
                  className="w-(--radix-popper-anchor-width) min-w-[200px]"
                >
                  {organizations.map((org) => (
                    <DropdownMenuItem
                      key={org.id}
                      className="flex flex-row items-center gap-x-2"
                      onClick={() => navigateToOrganization(org)}
                    >
                      <Avatar
                        name={org.name}
                        avatar_url={org.avatar_url}
                        className="h-6 w-6"
                      />
                      <span className="min-w-0 truncate">{org.name}</span>
                    </DropdownMenuItem>
                  ))}
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    onClick={() =>
                      CONFIG.IS_SANDBOX
                        ? router.push('/onboarding/sandbox')
                        : router.push('/onboarding/business')
                    }
                  >
                    New Organization
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={() => router.push('/dashboard/account')}
                  >
                    User Settings
                  </DropdownMenuItem>
                  {!CONFIG.IS_SANDBOX && (
                    <DropdownMenuItem
                      onClick={() =>
                        router.push('https://sandbox.outception.com/start')
                      }
                    >
                      Go to Sandbox
                    </DropdownMenuItem>
                  )}
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    onClick={() =>
                      router.push(`${CONFIG.BASE_URL}/v1/auth/logout`)
                    }
                  >
                    Logout
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </SidebarMenuItem>
          </SidebarMenu>
        )}
      </SidebarFooter>
    </Sidebar>
  )
}
