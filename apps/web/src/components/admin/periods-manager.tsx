import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { CalendarRange, Pencil, Plus, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Dialog } from '@/components/ui/dialog'
import {
  usePeriods,
  useCreatePeriod,
  useUpdatePeriod,
  useDeletePeriod,
} from '@/hooks/use-periods'
import { ApiError, type PeriodOut } from '@/lib/types'
import { formatDate } from '@/lib/date-utils'
import { cn } from '@/lib/utils'

type Editing = { mode: 'create' } | { mode: 'edit'; period: PeriodOut } | null

export function PeriodsManager() {
  const { t } = useTranslation()
  const { data: periods, isLoading } = usePeriods()
  const createPeriod = useCreatePeriod()
  const updatePeriod = useUpdatePeriod()
  const deletePeriod = useDeletePeriod()

  const [editing, setEditing] = useState<Editing>(null)
  const [name, setName] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<PeriodOut | null>(null)

  const openCreate = () => {
    setEditing({ mode: 'create' })
    setName('')
    setStartDate('')
    setEndDate('')
    setError(null)
  }

  const openEdit = (period: PeriodOut) => {
    setEditing({ mode: 'edit', period })
    setName(period.name)
    setStartDate(period.startDate.slice(0, 10))
    setEndDate(period.endDate.slice(0, 10))
    setError(null)
  }

  const handleSave = () => {
    if (!editing) return
    setError(null)
    if (!name.trim() || !startDate || !endDate) {
      setError(t('admin.periods.requiredFields'))
      return
    }
    if (endDate <= startDate) {
      setError(t('admin.periods.invalidRange'))
      return
    }

    const onError = (err: unknown) => {
      setError(
        err instanceof ApiError ? err.message : t('admin.periods.saveError')
      )
    }

    if (editing.mode === 'create') {
      createPeriod.mutate(
        { name: name.trim(), startDate, endDate },
        {
          onSuccess: () => setEditing(null),
          onError,
        }
      )
    } else {
      updatePeriod.mutate(
        {
          id: editing.period.id,
          dto: { name: name.trim(), startDate, endDate },
        },
        {
          onSuccess: () => setEditing(null),
          onError,
        }
      )
    }
  }

  const handleDelete = () => {
    if (!deleteTarget) return
    setError(null)
    deletePeriod.mutate(deleteTarget.id, {
      onSuccess: () => setDeleteTarget(null),
      onError: (err) => {
        setError(
          err instanceof ApiError ? err.message : t('admin.periods.deleteError')
        )
        setDeleteTarget(null)
      },
    })
  }

  const pending =
    createPeriod.isPending || updatePeriod.isPending || deletePeriod.isPending

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">{t('admin.periods.title')}</h2>
        <Button size="sm" onClick={openCreate}>
          <Plus className="h-3 w-3" />
          {t('admin.periods.create')}
        </Button>
      </div>

      {error && !editing && !deleteTarget && (
        <p className="text-sm text-destructive">{error}</p>
      )}

      {isLoading ? (
        <p className="text-muted-foreground">{t('common.loading')}</p>
      ) : !periods?.length ? (
        <div className="rounded-md border border-dashed p-8 text-center">
          <p className="text-muted-foreground">{t('admin.periods.empty')}</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-md border">
          <table className="w-full">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">
                  {t('admin.periods.name')}
                </th>
                <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">
                  {t('admin.periods.range')}
                </th>
                <th className="px-4 py-3 text-right text-sm font-medium text-muted-foreground">
                  {t('admin.periods.reportCount')}
                </th>
                <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">
                  {t('admin.periods.statusLabel')}
                </th>
                <th className="px-4 py-3 text-right text-sm font-medium text-muted-foreground">
                  {t('report.actions')}
                </th>
              </tr>
            </thead>
            <tbody>
              {periods.map((period) => (
                <tr key={period.id} className="border-b last:border-0">
                  <td className="px-4 py-3">
                    <span className="flex items-center gap-2 font-medium">
                      <CalendarRange className="h-4 w-4 text-muted-foreground" />
                      {period.name}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-muted-foreground">
                    {formatDate(period.startDate)} — {formatDate(period.endDate)}
                  </td>
                  <td className="px-4 py-3 text-right text-sm">
                    {period.reportCount}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={cn(
                        'inline-block rounded-full px-2 py-0.5 text-xs font-medium',
                        period.isArchived
                          ? 'bg-muted text-muted-foreground'
                          : 'bg-green-100 text-green-800'
                      )}
                    >
                      {period.isArchived
                        ? t('admin.periods.archived')
                        : t('admin.periods.active')}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex justify-end gap-1">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => openEdit(period)}
                      >
                        <Pencil className="h-3 w-3" />
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        disabled={period.reportCount > 0}
                        title={
                          period.reportCount > 0
                            ? t('admin.periods.deleteBlocked')
                            : t('common.delete')
                        }
                        onClick={() => {
                          setDeleteTarget(period)
                          setError(null)
                        }}
                      >
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Create / Edit dialog */}
      <Dialog
        open={editing !== null}
        onClose={() => setEditing(null)}
        title={
          editing?.mode === 'edit'
            ? t('admin.periods.editTitle')
            : t('admin.periods.createTitle')
        }
      >
        <div className="space-y-3">
          <div className="space-y-1.5">
            <Label htmlFor="periodName">{t('admin.periods.name')}</Label>
            <Input
              id="periodName"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="2026-fall"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="periodStart">{t('admin.periods.startDate')}</Label>
              <Input
                id="periodStart"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="periodEnd">{t('admin.periods.endDate')}</Label>
              <Input
                id="periodEnd"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
              />
            </div>
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setEditing(null)}>
              {t('common.cancel')}
            </Button>
            <Button onClick={handleSave} disabled={pending}>
              {t('common.save')}
            </Button>
          </div>
        </div>
      </Dialog>

      {/* Delete confirm */}
      <Dialog
        open={deleteTarget !== null}
        onClose={() => setDeleteTarget(null)}
        title={t('admin.periods.deleteTitle')}
      >
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">
            {t('admin.periods.deleteConfirm', { name: deleteTarget?.name })}
          </p>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>
              {t('common.cancel')}
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={pending}
            >
              {t('common.delete')}
            </Button>
          </div>
        </div>
      </Dialog>
    </div>
  )
}
