import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { AlertTriangle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { StatusBadge } from '@/components/ui/status-badge'
import { ReportLinks } from '@/components/ui/report-links'
import { ReportPoints } from '@/components/ui/report-points'
import { useReports, useSubmitReport, useDeleteReport } from '@/hooks/use-reports'
import { formatDate } from '@/lib/date-utils'

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
        <Button className="mt-4" onClick={() => navigate('/reports/new')}>
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
        {reports.map((report) => {
          const canSubmit =
            report.status === 'DRAFT' || report.status === 'CHANGES_REQUIRED'

          return (
            <div
              key={report.id}
              className="flex items-center justify-between rounded-md border p-4"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-medium">{report.criteriaCode}</span>
                  <StatusBadge status={report.status} />
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
                <ReportLinks links={report.links} />
              </div>

              <div className="flex items-center gap-2">
                <ReportPoints
                  calculated={report.calculatedPoints}
                  final={report.finalPoints}
                />

                {canSubmit && (
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
          )
        })}
      </div>
    </div>
  )
}
