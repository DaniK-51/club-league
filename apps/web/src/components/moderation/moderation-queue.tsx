import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Archive } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ModerationCard } from './moderation-card'
import { useReports, useArchiveReports } from '@/hooks/use-reports'
import type { ReportStatus } from '@/lib/types'

const STATUS_FILTERS: (ReportStatus | 'ALL')[] = [
  'ALL',
  'ON_MODERATION',
  'DISPUTED',
  'APPROVED',
  'CHANGES_REQUIRED',
  'COMPLETED',
  'CLOSED',
]

export function ModerationQueue() {
  const { t } = useTranslation()
  const { data: reports, isLoading } = useReports()
  const archiveReports = useArchiveReports()

  const [statusFilter, setStatusFilter] = useState<ReportStatus | 'ALL'>(
    'ON_MODERATION'
  )

  const filtered = useMemo(() => {
    if (!reports) return []
    if (statusFilter === 'ALL') return reports
    return reports.filter((r) => r.status === statusFilter)
  }, [reports, statusFilter])

  const counts = useMemo(() => {
    if (!reports) return {} as Record<string, number>
    const acc: Record<string, number> = { ALL: reports.length }
    for (const r of reports) {
      acc[r.status] = (acc[r.status] ?? 0) + 1
    }
    return acc
  }, [reports])

  if (isLoading) {
    return <p className="text-muted-foreground">{t('common.loading')}</p>
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap items-center gap-2">
        {STATUS_FILTERS.map((status) => (
          <button
            key={status}
            onClick={() => setStatusFilter(status)}
            className={`rounded-full px-3 py-1 text-sm transition-colors ${
              statusFilter === status
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted text-muted-foreground hover:bg-muted/80'
            }`}
          >
            {status === 'ALL'
              ? t('moderation.filterAll')
              : t(`report.status.${status}`)}
            {counts[status] != null && (
              <span className="ml-1 opacity-70">({counts[status]})</span>
            )}
          </button>
        ))}

        <div className="ml-auto">
          <Button
            variant="outline"
            size="sm"
            onClick={() => archiveReports.mutate('2026-fall')}
            disabled={archiveReports.isPending}
          >
            <Archive className="h-3 w-3" />
            {t('moderation.archivePeriod')}
          </Button>
        </div>
      </div>

      {/* Queue */}
      {filtered.length === 0 ? (
        <div className="rounded-md border border-dashed p-8 text-center">
          <p className="text-muted-foreground">{t('moderation.queueEmpty')}</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((report) => (
            <ModerationCard key={report.id} report={report} />
          ))}
        </div>
      )}
    </div>
  )
}
