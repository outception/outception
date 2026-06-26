'use client'

import { getServerURL } from '@/utils/api'
import { schemas } from '@outception-com/client'
import { Avatar, Button } from '@outception-com/orbit'
import Link from 'next/link'
import SharedLayout from './components/SharedLayout'

const OrganizationSelectionPage = ({
  authorizeResponse: { client, organizations },
  searchParams,
}: {
  authorizeResponse: schemas['AuthorizeResponseOrganization']
  searchParams: Record<string, string>
}) => {
  const serializedSearchParams = new URLSearchParams(searchParams).toString()
  const actionURL = `${getServerURL()}/v1/oauth2/consent?${serializedSearchParams}`

  const buildOrganizationSelectionURL = (
    organization: schemas['AuthorizeOrganization'],
  ) => {
    const updatedSearchParams = {
      ...searchParams,
      sub: organization.id,
    }
    return `?${new URLSearchParams(updatedSearchParams).toString()}`
  }

  const clientName = client.client_name || client.client_id
  const hasTerms = client.policy_uri || client.tos_uri
  const hasOrganizations = organizations.length > 0

  if (!hasOrganizations) {
    return (
      <SharedLayout
        client={client}
        introduction={
          <>
            <span className="dark:text-outception-200 font-medium text-gray-700">
              {clientName}
            </span>{' '}
            wants to access one of your organizations.
          </>
        }
      >
        <div className="dark:text-outception-400 text-center text-sm text-gray-500">
          You don&apos;t have an organization yet. Create one from your
          dashboard, then return to authorize this app.
        </div>
      </SharedLayout>
    )
  }

  return (
    <SharedLayout
      client={client}
      introduction={
        <>
          <span className="dark:text-outception-200 font-medium text-gray-700">
            {clientName}
          </span>{' '}
          wants to access one of your organizations. Select one:
        </>
      }
    >
      <form method="post" action={actionURL}>
        <div className="mb-6 flex w-full flex-col gap-3">
          {organizations.map((organization) => (
            <Link
              key={organization.id}
              href={buildOrganizationSelectionURL(organization)}
            >
              <div className="dark:bg-outception-700 dark:hover:bg-outception-600 flex w-full flex-row items-center gap-2 rounded-2xl border border-gray-200 bg-white px-2.5 py-3 text-sm transition-colors hover:border-gray-300 dark:border-white/5 dark:hover:border-white/5">
                <Avatar
                  className="h-8 w-8"
                  avatar_url={organization.avatar_url}
                  name={organization.slug}
                />
                {organization.slug}
              </div>
            </Link>
          ))}
        </div>
        <div className="grid w-full">
          <Button
            variant="secondary"
            className="grow"
            type="submit"
            name="action"
            value="deny"
          >
            Deny
          </Button>
        </div>
        {hasTerms && (
          <div className="mt-8 text-center text-sm text-gray-500">
            Before using this app, you can review {clientName}&apos;s{' '}
            {client.tos_uri && (
              <a
                className="dark:text-outception-300 text-gray-700"
                href={client.tos_uri}
              >
                Terms of Service
              </a>
            )}
            {client.tos_uri && client.policy_uri && ' and '}
            {client.policy_uri && (
              <a
                className="dark:text-outception-300 text-gray-700"
                href={client.policy_uri}
              >
                Privacy Policy
              </a>
            )}
            .
          </div>
        )}
      </form>
    </SharedLayout>
  )
}

export default OrganizationSelectionPage
