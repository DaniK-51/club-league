import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { AlertTriangle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { StatusBadge } from '@/components/ui/status-badge'
import { ReportLinks } from '@/components/ui/report-links'
import { ReportPoints } from '@/components/ui/report-points'
import { useReports } from '@/hooks/use-reports'
import { formatDate } from '@/lib/date-utils'

export function ReportList() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { data: reports, isLoading } = useReports()

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
        {reports.map((report) => (
          <div
            key={report.id}
            className="flex cursor-pointer items-center justify-between rounded-md border p-4 transition-colors hover:bg-muted/50"
            onClick={() => navigate(`/reports/${report.id}`)}
          >
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="font-medium">{report.criteriaCode}</span>
                <StatusBadge status={report.status} />
                {report.periodName && (
                  <span className="rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground">
                    {report.periodName}
                  </span>
                )}
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

            <ReportPoints
              calculated={report.calculatedPoints}
              final={report.finalPoints}
            />
          </div>
        ))}
      </div>
    </div>
  )
}
