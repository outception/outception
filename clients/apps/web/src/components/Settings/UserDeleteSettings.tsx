'use client'

import { useDeleteUser } from '@/hooks/queries'
import { useT } from '@/providers/locale'
import { CONFIG } from '@/utils/config'
import { Button } from '@outception-com/orbit'
import { useCallback, useState } from 'react'
import { ConfirmModal } from '../Modal/ConfirmModal'
import { toast } from '../Toast/use-toast'
import { SettingsGroup, SettingsGroupItem } from './SettingsGroup'

const TOAST_LONG_DURATION = 8000

export default function UserDeleteSettings() {
  const deleteUser = useDeleteUser()
  const t = useT()
  const [showDeleteModal, setShowDeleteModal] = useState(false)

  const handleDelete = useCallback(async () => {
    const { data, error } = await deleteUser.mutateAsync()

    if (error) {
      toast({
        title: t('account.danger.deletionFailed'),
        description: t('account.danger.deletionFailedDesc'),
        variant: 'error',
        duration: TOAST_LONG_DURATION,
      })
      return
    }

    if (data.deleted) {
      toast({
        title: t('account.danger.accountDeleted'),
        description: t('account.danger.accountDeletedDesc'),
        variant: 'success',
        duration: TOAST_LONG_DURATION,
      })
      window.location.href = `${CONFIG.BASE_URL}/v1/auth/logout`
    } else {
      const organizations = data.blocking_organizations ?? []
      const orgNames = organizations.map((o) => o.name).join(', ')
      toast({
        title: t('account.danger.deletionBlocked'),
        description:
          t('account.danger.deletionBlockedDesc') +
          (orgNames
            ? ' ' + t('account.danger.blockingOrgs', { orgs: orgNames })
            : ''),
        variant: 'error',
        duration: TOAST_LONG_DURATION,
      })
      setShowDeleteModal(false)
    }
  }, [deleteUser, t])

  return (
    <>
      <SettingsGroup>
        <SettingsGroupItem
          title={t('account.danger.deleteAccount')}
          description={t('account.danger.deleteAccountDesc')}
        >
          <Button
            variant="destructive"
            onClick={() => setShowDeleteModal(true)}
            size="sm"
          >
            {t('account.danger.delete')}
          </Button>
        </SettingsGroupItem>
      </SettingsGroup>

      <ConfirmModal
        isShown={showDeleteModal}
        hide={() => setShowDeleteModal(false)}
        title={t('account.danger.deleteAccount')}
        description={t('account.danger.confirmDesc')}
        body={
          <div className="dark:text-outception-400 text-sm text-gray-600">
            <p className="mb-2">{t('account.danger.whenYouDelete')}</p>
            <ul className="list-inside list-disc space-y-1">
              <li>{t('account.danger.bulletEmail')}</li>
              <li>{t('account.danger.bulletOauth')}</li>
              <li>{t('account.danger.bulletOrgs')}</li>
            </ul>
          </div>
        }
        onConfirm={handleDelete}
        destructive
        destructiveText={t('account.danger.delete')}
      />
    </>
  )
}
