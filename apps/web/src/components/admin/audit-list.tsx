import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useAuditLog } from '@/hooks/use-admin'
import { formatDate } from '@/lib/date-utils'

const PAGE_SIZE = 25

export function AuditList() {
  const { t } = useTranslation()
  const [entityType, setEntityType] = useState('')
  const [entityId, setEntityId] = useState('')
  const [offset, setOffset] = useState(0)

  const { data, isLoading } = useAuditLog(
    entityType || undefined,
    entityId || undefined,
    PAGE_SIZE,
    offset
  )

  const items = data?.items ?? []
  const total = data?.total ?? 0
  const page = Math.floor(offset / PAGE_SIZE) + 1
  const totalPages = Math.ceil(total / PAGE_SIZE)

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">{t('admin.audit.title')}</h2>

      {/* Filters */}
      <div className="flex flex-wrap gap-4">
        <div className="space-y-1.5">
          <Label htmlFor="entityType">{t('admin.audit.entityType')}</Label>
          <select
            id="entityType"
            value={entityType}
            onChange={(e) => {
              setEntityType(e.target.value)
              setOffset(0)
            }}
            className="flex h-9 w-40 rounded-md border border-input bg-transparent px-3 py-1 text-sm"
          >
            <option value="">{t('admin.audit.allTypes')}</option>
            <option value="report">report</option>
            <option value="rule">rule</option>
            <option value="user">user</option>
          </select>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="entityId">{t('admin.audit.entityId')}</Label>
          <Input
            id="entityId"
            value={entityId}
            onChange={(e) => {
              setEntityId(e.target.value)
              setOffset(0)
            }}
            placeholder="uuid"
            className="w-48"
          />
        </div>
      </div>

      {/* Table */}
      {isLoading ? (
        <p className="text-muted-foreground">{t('common.loading')}</p>
      ) : items.length === 0 ? (
        <div className="rounded-md border border-dashed p-8 text-center">
          <p className="text-muted-foreground">{t('admin.audit.empty')}</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-md border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="px-3 py-2 text-left font-medium text-muted-foreground">#</th>
                <th className="px-3 py-2 text-left font-medium text-muted-foreground">
                  {t('admin.audit.entity')}
                </th>
                <th className="px-3 py-2 text-left font-medium text-muted-foreground">
                  {t('admin.audit.action')}
                </th>
                <th className="px-3 py-2 text-left font-medium text-muted-foreground">
                  {t('admin.audit.performedBy')}
                </th>
                <th className="px-3 py-2 text-left font-medium text-muted-foreground">
                  {t('admin.audit.date')}
                </th>
                <th className="px-3 py-2 text-left font-medium text-muted-foreground">
                  {t('admin.audit.reason')}
                </th>
              </tr>
            </thead>
            <tbody>
              {items.map((entry) => (
                <tr key={entry.id} className="border-b last:border-0">
                  <td className="px-3 py-2 text-muted-foreground">{entry.seq}</td>
                  <td className="px-3 py-2">
                    <span className="font-mono text-xs">
                      {entry.entityType}:{entry.entityId.slice(0, 8)}…
                    </span>
                  </td>
                  <td className="px-3 py-2">
                    <span className="rounded bg-muted px-1.5 py-0.5 text-xs">
                      {entry.action}
                    </span>
                  </td>
                  <td className="px-3 py-2">
                    <div>
                      <span>{entry.performedByName}</span>
                      <span className="ml-1 text-xs text-muted-foreground">
                        ({entry.performedByRole})
                      </span>
                    </div>
                  </td>
                  <td className="px-3 py-2 text-muted-foreground">
                    {formatDate(entry.performedAt)}
                  </td>
                  <td className="px-3 py-2 text-xs text-muted-foreground">
                    {entry.reason ?? '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            {t('admin.audit.page', { page, totalPages, total })}
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
              disabled={offset === 0}
            >
              <ChevronLeft className="h-3 w-3" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setOffset(offset + PAGE_SIZE)}
              disabled={offset + PAGE_SIZE >= total}
            >
              <ChevronRight className="h-3 w-3" />
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
