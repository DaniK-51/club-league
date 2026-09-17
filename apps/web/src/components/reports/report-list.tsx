import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { AlertTriangle, ExternalLink } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useReports, useSubmitReport, useDeleteReport } from '@/hooks/use-reports'
import { formatDate } from '@/lib/date-utils'
import type { ReportStatus } from '@/lib/types'

const STATUS_COLORS: Record<ReportStatus, string> = {
  DRAFT: 'bg-muted text-muted-foreground',
  ON_MODERATION: 'bg-blue-100 text-blue-800',
  CHANGES_REQUIRED: 'bg-yellow-100 text-yellow-800',
  APPROVED: 'bg-green-100 text-green-800',
  DISPUTED: 'bg-orange-100 text-orange-800',
  COMPLETED: 'bg-emerald-100 text-emerald-800',
  CLOSED: 'bg-red-100 text-red-800',
  ARCHIVED: 'bg-gray-100 text-gray-800',
}

export function ReportList() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { data: reports, isLoading } = useReports()
  const submitReport = useSubmitReport()
  const deleteReport = useDeleteReport()

  if (isLoading) {
    return <p className="text-muted-foreground">{t('common.loading')}</p>
  }

  if (!reports?.length) {
    return (
      <div className="rounded-md border border-dashed p-8 text-center">
        <p className="text-muted-foreground">{t('reports.empty')}</p>
        <Button
          className="mt-4"
          onClick={() => navigate('/reports/new')}
        >
          {t('report.create')}
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between">
        <h2 className="text-lg font-semibold">{t('reports.listTitle')}</h2>
        <Button onClick={() => navigate('/reports/new')}>
          {t('report.create')}
        </Button>
      </div>

      <div className="space-y-2">
        {reports.map((report) => (
          <div
            key={report.id}
            className="flex items-center justify-between rounded-md border p-4"
          >
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="font-medium">{report.criteriaCode}</span>
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[report.status]}`}
                >
                  {t(`report.status.${report.status}`)}
                </span>
                {report.isOverdue && (
                  <span className="flex items-center gap-1 text-xs text-yellow-600">
                    <AlertTriangle className="h-3 w-3" />
                    {t('report.overdueBadge')}
                  </span>
                )}
              </div>
              <p className="text-sm text-muted-foreground">
                {formatDate(report.activityDate)}
              </p>
              {report.links.length > 0 && (
                <div className="flex gap-1">
                  {report.links.map((link, i) => (
                    <a
                      key={i}
                      href={link.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-muted-foreground hover:underline"
                    >
                      <ExternalLink className="inline h-3 w-3" /> {link.domain}
                    </a>
                  ))}
                </div>
              )}
            </div>

            <div className="flex items-center gap-2">
              {report.calculatedPoints != null && (
                <span className="text-sm font-medium">
                  {report.calculatedPoints} {t('report.pointsUnit')}
                </span>
              )}
              {report.finalPoints != null && (
                <span className="text-sm font-semibold text-primary">
                  {report.finalPoints} {t('report.pointsUnit')}
                </span>
              )}

              {(report.status === 'DRAFT' ||
                report.status === 'CHANGES_REQUIRED') && (
                <div className="flex gap-1">
                  <Button
                    size="sm"
                    onClick={() => submitReport.mutate(report.id)}
                    disabled={submitReport.isPending}
                  >
                    {t('report.submit')}
                  </Button>
                  {report.status === 'DRAFT' && (
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={() => deleteReport.mutate(report.id)}
                      disabled={deleteReport.isPending}
                    >
                      {t('common.delete')}
                    </Button>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
