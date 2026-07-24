'use client'

import { InlineModal, InlineModalHeader } from '@outception-com/orbit'
import { useModal } from '@/components/Modal/useModal'
import { useT } from '@/providers/locale'
import {
  useDeleteOrganizationAccessToken,
  useOrganizationAccessTokens,
  useUpdateOrganizationAccessToken,
} from '@/hooks/queries'
import { enums, schemas } from '@outception-com/client'
import { Button } from '@outception-com/orbit'
import CopyToClipboardInput from '@outception-com/ui/components/atoms/CopyToClipboardInput'
import FormattedDateTime from '@outception-com/ui/components/atoms/FormattedDateTime'
import { Input } from '@outception-com/orbit'
import { ListGroup } from '@outception-com/orbit'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@outception-com/orbit'
import Banner from '@outception-com/ui/components/molecules/Banner'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@outception-com/ui/components/ui/form'
import { useCallback, useState } from 'react'
import { useForm, useFormContext } from 'react-hook-form'
import { ConfirmModal } from '../Modal/ConfirmModal'
import { toast, useToast } from '../Toast/use-toast'
import { CreateAccessTokenModal } from './CreateAccessTokenModal'
import { TreeMultiSelect } from './TreeMultiSelect'

export interface AccessTokenCreate {
  comment: string
  expires_in: string | null | 'no-expiration'
  scopes: Array<schemas['AvailableScope']>
}

interface AccessTokenUpdate {
  comment: string
  scopes: Array<schemas['AvailableScope']>
}

export const AccessTokenForm = ({ update }: { update?: boolean }) => {
  const { control } = useFormContext<AccessTokenCreate | AccessTokenUpdate>()
  const t = useT()

  return (
    <>
      <FormField
        control={control}
        name="comment"
        rules={{
          required: t('settings.tokens.nameRequired'),
        }}
        render={({ field }) => (
          <FormItem>
            <FormLabel>{t('settings.tokens.name')}</FormLabel>
            <FormControl>
              <Input
                {...field}
                placeholder={t('settings.tokens.namePlaceholder')}
              />
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />
      {!update && (
        <FormField
          control={control}
          name="expires_in"
          rules={{ required: t('settings.tokens.expirationRequired') }}
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t('settings.tokens.expiration')}</FormLabel>
              <FormControl>
                <Select
                  onValueChange={field.onChange}
                  defaultValue={field.value || ''}
                >
                  <SelectTrigger>
                    <SelectValue
                      placeholder={t('settings.tokens.expirationPlaceholder')}
                    />
                  </SelectTrigger>
                  <SelectContent>
                    {[1, 7, 30, 90, 180, 365].map((days) => (
                      <SelectItem key={days} value={`P${days}D`}>
                        {t(
                          days > 1
                            ? 'settings.tokens.days'
                            : 'settings.tokens.day',
                          { days },
                        )}
                      </SelectItem>
                    ))}
                    <SelectItem value="no-expiration">
                      <span className="text-red-500 dark:text-red-400">
                        {t('settings.tokens.noExpiration')}
                      </span>
                    </SelectItem>
                  </SelectContent>
                </Select>
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
      )}
      <FormField
        control={control}
        name="scopes"
        render={({ field }) => (
          <FormItem>
            <FormControl>
              <TreeMultiSelect
                title={t('settings.tokens.scopes')}
                options={enums.availableScopeValues}
                value={field.value ?? []}
                onChange={field.onChange}
              />
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />
    </>
  )
}

interface UpdateAccessTokenModalProps {
  token: schemas['OrganizationAccessToken']
  onSuccess: (token: schemas['OrganizationAccessToken']) => void
  onHide: () => void
}

const UpdateAccessTokenModal = ({
  token,
  onSuccess,
  onHide,
}: UpdateAccessTokenModalProps) => {
  const updateToken = useUpdateOrganizationAccessToken(token.id)
  const form = useForm<AccessTokenUpdate>({
    defaultValues: {
      ...token,
      scopes: token.scopes as schemas['AvailableScope'][],
    },
  })
  const { handleSubmit } = form
  const { toast } = useToast()
  const t = useT()

  const onUpdate = useCallback(
    async (data: AccessTokenUpdate) => {
      const { data: updated } = await updateToken.mutateAsync({
        comment: data.comment ? data.comment : '',
        scopes: data.scopes,
      })
      if (updated) {
        onSuccess(updated)
        toast({
          title: t('settings.tokens.updated'),
          description: t('settings.tokens.updatedDesc', {
            name: updated.comment ?? '',
          }),
        })
      }
    },
    [updateToken, onSuccess, toast, t],
  )

  return (
    <div className="flex flex-col overflow-y-auto">
      <InlineModalHeader hide={onHide}>
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-xl">{t('settings.tokens.updateTitle')}</h2>
        </div>
      </InlineModalHeader>
      <div className="flex flex-col gap-y-8 p-8">
        <Form {...form}>
          <form
            onSubmit={handleSubmit(onUpdate)}
            className="max-w-[700px] space-y-8"
          >
            <AccessTokenForm update />
            <Button type="submit">{t('settings.tokens.updateButton')}</Button>
          </form>
        </Form>
      </div>
    </div>
  )
}

const AccessTokenItem = ({
  token,
  rawToken,
  minimal,
}: {
  token: schemas['OrganizationAccessToken']
  rawToken?: string
  minimal?: boolean
}) => {
  const {
    isShown: updateModalShown,
    show: showUpdateModal,
    hide: hideUpdateModal,
  } = useModal()

  const {
    isShown: deleteModalShown,
    show: showDeleteModal,
    hide: hideDeleteModal,
  } = useModal()

  const deleteToken = useDeleteOrganizationAccessToken()
  const t = useT()

  const onDelete = useCallback(async () => {
    deleteToken.mutateAsync(token).then(({ error }) => {
      if (error) {
        toast({
          title: t('settings.tokens.deleteError'),
          description:
            error.detail?.[0]?.msg ?? t('settings.tokens.unknownError'),
        })
        return
      }
      toast({
        title: t('settings.tokens.deleted'),
        description: t('settings.tokens.deletedDesc', {
          name: token.comment ?? '',
        }),
      })
    })
  }, [token, deleteToken, t])

  return (
    <div className="flex flex-col gap-y-4">
      <div className="flex flex-row items-center justify-between">
        <div className="flex flex-row">
          <div className="gap-y flex flex-col">
            <h3 className="text-md">{token.comment}</h3>
            {!minimal && (
              <p className="dark:text-outception-400 text-sm text-gray-500">
                {token.expires_at ? (
                  new Date(token.expires_at) < new Date() ? (
                    <span className="text-red-500 dark:text-red-400">
                      {t('settings.tokens.expiredOn')}{' '}
                      <FormattedDateTime
                        datetime={token.expires_at}
                        dateStyle="long"
                      />
                    </span>
                  ) : (
                    <>
                      {t('settings.tokens.expiresOn')}{' '}
                      <FormattedDateTime
                        datetime={token.expires_at}
                        dateStyle="long"
                      />
                    </>
                  )
                ) : (
                  <span className="text-red-500 dark:text-red-400">
                    {t('settings.tokens.neverExpires')}
                  </span>
                )}{' '}
                —{' '}
                {token.last_used_at ? (
                  <>
                    {t('settings.tokens.lastUsedOn')}{' '}
                    <FormattedDateTime
                      datetime={token.last_used_at}
                      dateStyle="long"
                    />
                  </>
                ) : (
                  t('settings.tokens.neverUsed')
                )}
              </p>
            )}
          </div>
        </div>{' '}
        <div className="dark:text-outception-400 flex flex-row items-center gap-2 text-gray-500">
          <Button onClick={showUpdateModal} size="sm">
            {t('settings.tokens.update')}
          </Button>
          <Button onClick={showDeleteModal} variant="destructive" size="sm">
            {t('settings.tokens.revoke')}
          </Button>
        </div>
      </div>
      {rawToken && (
        <>
          <CopyToClipboardInput
            value={rawToken}
            onCopy={() => {
              toast({
                title: t('settings.tokens.copied'),
              })
            }}
            variant="mono"
          />
          <Banner color="blue">
            <span className="text-sm">{t('settings.tokens.copySafe')}</span>
          </Banner>
        </>
      )}
      <InlineModal
        isShown={updateModalShown}
        hide={hideUpdateModal}
        modalContent={
          <UpdateAccessTokenModal
            token={token}
            onSuccess={hideUpdateModal}
            onHide={hideUpdateModal}
          />
        }
      />
      <ConfirmModal
        isShown={deleteModalShown}
        hide={hideDeleteModal}
        onConfirm={onDelete}
        title={t('settings.tokens.revokeTitle')}
        description={t('settings.tokens.revokeDesc')}
        destructive
        destructiveText={t('settings.tokens.revoke')}
        confirmPrompt={token.comment}
      />
    </div>
  )
}

interface OrganizationAccessTokensSettingsProps {
  organization: schemas['Organization']
  singleTokenMode?: boolean
  onTokenCreated?: (token: string) => void
  minimal?: boolean
}

const OrganizationAccessTokensSettings = ({
  organization,
  singleTokenMode = false,
  onTokenCreated,
  minimal = false,
}: OrganizationAccessTokensSettingsProps) => {
  const tokens = useOrganizationAccessTokens(organization.id)
  const t = useT()
  const [createdToken, setCreatedToken] =
    useState<schemas['OrganizationAccessTokenCreateResponse']>()

  const {
    isShown: createModalShown,
    show: showCreateModal,
    hide: hideCreateModal,
  } = useModal()

  const onCreate = (
    token: schemas['OrganizationAccessTokenCreateResponse'],
  ) => {
    hideCreateModal()
    setCreatedToken(token)
    onTokenCreated?.(token.token)
  }

  const hasTokens =
    (tokens.data?.items && tokens.data.items.length > 0) || createdToken
  const showNewTokenButton = !singleTokenMode || !hasTokens

  const hasExistingTokens = tokens.data?.items && tokens.data.items.length > 0

  // Minimal mode: just show a button or the created token
  if (minimal) {
    return (
      <div className="flex w-full flex-col items-start gap-y-4">
        {hasExistingTokens
          ? tokens.data?.items.map((token) => {
              const isNewToken =
                token.id === createdToken?.organization_access_token.id
              return (
                <div
                  key={token.id}
                  className="dark:ring-outception-700 dark:bg-outception-800 w-full rounded-2xl bg-transparent p-5 ring-1 ring-gray-200"
                >
                  <AccessTokenItem
                    token={token}
                    minimal={minimal}
                    rawToken={isNewToken ? createdToken?.token : undefined}
                  />
                </div>
              )
            })
          : showNewTokenButton && (
              <Button onClick={showCreateModal} size="sm">
                {t('settings.tokens.createAccess')}
              </Button>
            )}
        <InlineModal
          isShown={createModalShown}
          hide={hideCreateModal}
          modalContent={
            <CreateAccessTokenModal
              organization={organization}
              onSuccess={onCreate}
              onHide={hideCreateModal}
            />
          }
        />
      </div>
    )
  }

  return (
    <div className="flex w-full flex-col">
      <ListGroup>
        {hasExistingTokens ? (
          tokens.data?.items.map((token) => {
            const isNewToken =
              token.id === createdToken?.organization_access_token.id

            return (
              <ListGroup.Item key={token.id}>
                <AccessTokenItem
                  token={token}
                  rawToken={isNewToken ? createdToken?.token : undefined}
                />
              </ListGroup.Item>
            )
          })
        ) : (
          <ListGroup.Item>
            <p className="dark:text-outception-400 text-sm text-gray-500">
              {t('settings.tokens.empty')}
            </p>
          </ListGroup.Item>
        )}
        {showNewTokenButton && (
          <ListGroup.Item>
            <div className="flex flex-row items-center gap-x-4">
              <Button asChild onClick={showCreateModal} size="sm">
                {t('settings.tokens.create')}
              </Button>
            </div>
          </ListGroup.Item>
        )}
        <InlineModal
          isShown={createModalShown}
          hide={hideCreateModal}
          modalContent={
            <CreateAccessTokenModal
              organization={organization}
              onSuccess={onCreate}
              onHide={hideCreateModal}
            />
          }
        />
      </ListGroup>
    </div>
  )
}

export default OrganizationAccessTokensSettings
