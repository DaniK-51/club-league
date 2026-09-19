import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Archive } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Dialog } from '@/components/ui/dialog'
import { SelectField } from '@/components/ui/form-fields'
import { usePeriods } from '@/hooks/use-periods'
import { useArchiveReports } from '@/hooks/use-reports'
import { ApiError } from '@/lib/types'

interface ArchiveDialogProps {
  open: boolean
  onClose: () => void
}

export function ArchiveDialog({ open, onClose }: ArchiveDialogProps) {
  const { t } = useTranslation()
  const { data: periods } = usePeriods(open)
  const archiveReports = useArchiveReports()

  const activePeriods = (periods ?? []).filter((p) => !p.isArchived)
  const defaultPeriod = activePeriods[0]?.name ?? ''
  const [period, setPeriod] = useState('')
  const [error, setError] = useState<string | null>(null)

  const selected = period || defaultPeriod

  const handleArchive = () => {
    if (!selected) return
    setError(null)
    archiveReports.mutate(selected, {
      onSuccess: () => {
        setPeriod('')
        onClose()
      },
      onError: (err) => {
        setError(
          err instanceof ApiError ? err.message : t('moderation.archiveError')
        )
      },
    })
  }

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={t('moderation.archivePeriod')}
    >
      <div className="space-y-3">
        <p className="text-sm text-muted-foreground">
          {t('moderation.archiveHint')}
        </p>
        <SelectField
          label={t('moderation.archivePeriodSelect')}
          value={selected}
          options={activePeriods.map((p) => ({
            value: p.name,
            label: `${p.name} (${formatRange(p.startDate, p.endDate)})`,
          }))}
          onChange={setPeriod}
        />
        {error && <p className="text-sm text-destructive">{error}</p>}
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>
            {t('common.cancel')}
          </Button>
          <Button
            onClick={handleArchive}
            disabled={!selected || archiveReports.isPending}
          >
            <Archive className="h-3 w-3" />
            {t('moderation.archiveConfirm')}
          </Button>
        </div>
      </div>
    </Dialog>
  )
}

function formatRange(start: string, end: string): string {
  return `${start.slice(0, 10)} → ${end.slice(0, 10)}`
}
