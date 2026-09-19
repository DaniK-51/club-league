import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ArrowLeft, AlertTriangle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { StatusBadge } from '@/components/ui/status-badge'
import { AuditChat } from './audit-chat'
import { ReportSidebar } from './report-sidebar'
import { useReport } from '@/hooks/use-reports'
import { useCriteria } from '@/hooks/use-reports'
import { useAuthStore } from '@/store/auth.store'

export function ReportDetail() {
  const { id } = useParams<{ id: string }>()
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)

  const { data: report, isLoading, error } = useReport(id ?? '')
  const { data: criteriaList } = useCriteria()

  const isModerator = user?.role === 'MODERATOR'
  const backPath = isModerator ? '/moderation' : '/reports'

  // Find the rule for this report's criteria
  const criteria = criteriaList?.find((c) => c.code === report?.criteriaCode)
  const rule = criteria?.rules?.[0]
  const criteriaName = criteria
    ? i18n.language === 'ru'
      ? criteria.nameRu
      : criteria.nameEn
    : undefined

  if (isLoading) {
    return <p className="text-muted-foreground">{t('common.loading')}</p>
  }

  if (error || !report) {
    return (
      <div className="space-y-4">
        <p className="text-muted-foreground">{t('report.notFound')}</p>
        <Button variant="outline" onClick={() => navigate(backPath)}>
          <ArrowLeft className="h-3 w-3" />
          {t('common.back')}
        </Button>
      </div>
    )
  }

  // Moderator cannot see drafts
  if (isModerator && report.status === 'DRAFT') {
    return (
      <div className="space-y-4">
        <p className="text-muted-foreground">
          {t('report.moderatorCannotSeeDraft')}
        </p>
        <Button variant="outline" onClick={() => navigate(backPath)}>
          <ArrowLeft className="h-3 w-3" />
          {t('nav.moderation')}
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Back button */}
      <Button
        variant="ghost"
        size="sm"
        onClick={() => navigate(backPath)}
        className="-ml-2"
      >
        <ArrowLeft className="h-3 w-3" />
        {isModerator ? t('nav.moderation') : t('nav.reports')}
      </Button>

      {/* Title */}
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-bold">
          {report.criteriaCode}
        </h1>
        <StatusBadge status={report.status} />
        {report.isOverdue && (
          <span className="flex items-center gap-1 text-sm text-yellow-600">
            <AlertTriangle className="h-4 w-4" />
            {t('report.overdueBadge')}
          </span>
        )}
      </div>

      {/* GitHub Issues layout: main content + sidebar */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_300px]">
        {/* Main: audit chat */}
        <div className="min-w-0">
          <AuditChat reportId={report.id} />
        </div>

        {/* Sidebar: interactive elements */}
        <div className="lg:border-l lg:pl-6">
          <ReportSidebar
            report={report}
            rule={rule}
            criteriaName={criteriaName}
            onNavigateBack={() => navigate(backPath)}
          />
        </div>
      </div>
    </div>
  )
}
