'use client'

import {
  DataTable,
  DataTableColumnHeader,
  Status,
  Text,
  type DataTableColumnDef,
  type DataTablePaginationState,
  type DataTableSortingState,
  type StatusColor,
} from '@outception-com/orbit'
import { useMemo, useState } from 'react'

interface Promotion {
  id: string
  advertiser: string
  email: string
  amount: number
  status: 'active' | 'queued' | 'expired'
}

const PROMOTIONS: Promotion[] = [
  {
    id: 'promo_01',
    advertiser: 'Acme AI',
    email: 'ops@acme.ai',
    amount: 4900,
    status: 'active',
  },
  {
    id: 'promo_02',
    advertiser: 'Nimbus Labs',
    email: 'billing@nimbus.dev',
    amount: 1200,
    status: 'queued',
  },
  {
    id: 'promo_03',
    advertiser: 'Quanta',
    email: 'finance@quanta.io',
    amount: 9900,
    status: 'active',
  },
  {
    id: 'promo_04',
    advertiser: 'Helix',
    email: 'team@helix.sh',
    amount: 2500,
    status: 'expired',
  },
  {
    id: 'promo_05',
    advertiser: 'Orbit Tools',
    email: 'hi@orbit.tools',
    amount: 7300,
    status: 'active',
  },
  {
    id: 'promo_06',
    advertiser: 'Vector',
    email: 'pay@vector.ai',
    amount: 1800,
    status: 'queued',
  },
  {
    id: 'promo_07',
    advertiser: 'Drift',
    email: 'accounts@drift.app',
    amount: 6400,
    status: 'active',
  },
  {
    id: 'promo_08',
    advertiser: 'Pulse',
    email: 'billing@pulse.co',
    amount: 3100,
    status: 'expired',
  },
]

const statusColor: Record<Promotion['status'], StatusColor> = {
  active: 'green',
  queued: 'yellow',
  expired: 'gray',
}

const formatAmount = (cents: number) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(
    cents / 100,
  )

const columns: DataTableColumnDef<Promotion>[] = [
  {
    accessorKey: 'advertiser',
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Advertiser" />
    ),
    cell: ({ row }) => <Text>{row.original.advertiser}</Text>,
  },
  {
    accessorKey: 'email',
    enableSorting: false,
    header: 'Email',
    cell: ({ row }) => <Text color="default">{row.original.email}</Text>,
  },
  {
    accessorKey: 'amount',
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Amount" />
    ),
    cell: ({ row }) => (
      <Text monospace>{formatAmount(row.original.amount)}</Text>
    ),
  },
  {
    accessorKey: 'status',
    enableSorting: false,
    header: 'Status',
    cell: ({ row }) => (
      <Status
        status={row.original.status}
        color={statusColor[row.original.status]}
        size="small"
      />
    ),
  },
]

export function PromotionsTableDemo() {
  const [pagination, setPagination] = useState<DataTablePaginationState>({
    pageIndex: 0,
    pageSize: 20,
  })
  const [sorting, setSorting] = useState<DataTableSortingState>([])

  const sorted = useMemo(() => {
    const sort = sorting[0]
    if (!sort) return PROMOTIONS
    const rows = [...PROMOTIONS]
    rows.sort((a, b) => {
      const key = sort.id as keyof Promotion
      if (a[key] < b[key]) return sort.desc ? 1 : -1
      if (a[key] > b[key]) return sort.desc ? -1 : 1
      return 0
    })
    return rows
  }, [sorting])

  const page = useMemo(() => {
    const start = pagination.pageIndex * pagination.pageSize
    return sorted.slice(start, start + pagination.pageSize)
  }, [sorted, pagination])

  return (
    <DataTable
      columns={columns}
      data={page}
      rowCount={PROMOTIONS.length}
      isLoading={false}
      pagination={pagination}
      onPaginationChange={setPagination}
      sorting={sorting}
      onSortingChange={setSorting}
    />
  )
}
