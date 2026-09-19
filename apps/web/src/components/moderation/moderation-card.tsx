import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { Check, X, MessageSquarePlus, AlertTriangle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { StatusBadge } from '@/components/ui/status-badge'
import { ReportLinks } from '@/components/ui/report-links'
import { ReportPoints } from '@/components/ui/report-points'
import { useModerateReport } from '@/hooks/use-reports'
import { formatDate } from '@/lib/date-utils'
import { ApiError, type ReportResponse } from '@/lib/types'
import { cn } from '@/lib/utils'

interface ModerationCardProps {
  report: ReportResponse
}

export function ModerationCard({ report }: ModerationCardProps) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const moderateReport = useModerateReport()

  const [activeAction, setActiveAction] = useState<
    'CHANGES_REQUIRED' | 'CLOSED' | null
  >(null)
  const [comment, setComment] = useState('')
  const [error, setError] = useState<string | null>(null)

  const canModerate =
    report.status === 'ON_MODERATION' || report.status === 'DISPUTED'

  const handleQuickAction = (
    status: 'APPROVED' | 'CHANGES_REQUIRED' | 'CLOSED',
    actionComment?: string
  ) => {
    setError(null)

    moderateReport.mutate(
      {
        id: report.id,
        dto: {
          status,
          comment: actionComment?.trim() || '',
        },
      },
      {
        onSuccess: () => {
          setActiveAction(null)
          setComment('')
        },
        onError: (err) => {
          setError(
            err instanceof ApiError ? err.message : t('moderation.actionError')
          )
        },
      }
    )
  }

  return (
    <div
      className={cn(
        'cursor-pointer rounded-md border p-4 transition-colors hover:bg-muted/30',
        report.isOverdue && 'border-yellow-300 bg-yellow-50/50'
      )}
      onClick={() => navigate(`/reports/${report.id}`)}
    >
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="font-semibold">{report.criteriaCode}</span>
            <span className="text-sm text-muted-foreground">
              {report.clubName}
            </span>
            <StatusBadge status={report.status} />
            {report.periodName && (
              <span className="rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground">
                {report.periodName}
              </span>
            )}
            {report.isOverdue && (
              <span className="flex items-center gap-1 text-xs text-yellow-700">
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

      {/* Quick action buttons */}
      {canModerate && (
        <div className="mt-3 flex flex-wrap items-center gap-2" onClick={(e) => e.stopPropagation()}>
          {activeAction === null && (
            <>
              <Button
                size="sm"
                variant="outline"
                onClick={() => handleQuickAction('APPROVED')}
                disabled={moderateReport.isPending}
              >
                <Check className="h-3 w-3" />
                {t('moderation.approve')}
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => setActiveAction('CHANGES_REQUIRED')}
              >
                <MessageSquarePlus className="h-3 w-3" />
                {t('moderation.requestChanges')}
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => setActiveAction('CLOSED')}
              >
                <X className="h-3 w-3" />
                {t('moderation.reject')}
              </Button>
            </>
          )}

          {/* Inline comment for changes/reject */}
          {activeAction !== null && (
            <div className="flex w-full flex-col gap-2">
              <Textarea
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder={t('moderation.commentPlaceholder')}
                rows={2}
              />
              {error && (
                <p className="text-xs text-destructive">{error}</p>
              )}
              <div className="flex gap-2">
                <Button
                  size="sm"
                  onClick={() => handleQuickAction(activeAction, comment)}
                  disabled={moderateReport.isPending || !comment.trim()}
                >
                  {activeAction === 'CHANGES_REQUIRED'
                    ? t('moderation.requestChanges')
                    : t('moderation.reject')}
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => {
                    setActiveAction(null)
                    setComment('')
                    setError(null)
                  }}
                >
                  {t('common.cancel')}
                </Button>
              </div>
            </div>
          )}

          {activeAction === null && error && (
            <p className="text-xs text-destructive">{error}</p>
          )}
        </div>
      )}
    </div>
  )
}
