import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { Check, X, MessageSquarePlus, AlertTriangle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { StatusBadge } from '@/components/ui/status-badge'
import { ReportLinks } from '@/components/ui/report-links'
import { ReportPoints } from '@/components/ui/report-points'
import { CommentThread } from './comment-thread'
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

  const [showActions, setShowActions] = useState(false)
  const [comment, setComment] = useState('')
  const [finalPoints, setFinalPoints] = useState('')
  const [error, setError] = useState<string | null>(null)

  const canModerate =
    report.status === 'ON_MODERATION' || report.status === 'DISPUTED'

  const needsComment = (status: string) =>
    status === 'CHANGES_REQUIRED' ||
    (status === 'APPROVED' && finalPoints !== '')

  const resetForm = () => {
    setShowActions(false)
    setComment('')
    setFinalPoints('')
    setError(null)
  }

  const handleModerate = (
    status: 'APPROVED' | 'CHANGES_REQUIRED' | 'CLOSED'
  ) => {
    setError(null)

    if (needsComment(status) && !comment.trim()) {
      setError(t('moderation.commentRequired'))
      return
    }

    moderateReport.mutate(
      {
        id: report.id,
        dto: {
          status,
          comment: comment.trim(),
          ...(finalPoints !== '' ? { finalPoints: Number(finalPoints) } : {}),
        },
      },
      {
        onSuccess: resetForm,
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
        'rounded-md border p-4',
        report.isOverdue && 'border-yellow-300 bg-yellow-50/50'
      )}
    >
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <button
              onClick={() => navigate(`/reports/${report.id}`)}
              className="font-semibold text-primary hover:underline"
            >
              {report.criteriaCode}
            </button>
            <span className="text-sm text-muted-foreground">
              {report.clubName}
            </span>
            <StatusBadge status={report.status} />
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

        <div className="flex items-center gap-3">
          <ReportPoints
            calculated={report.calculatedPoints}
            final={report.finalPoints}
            showLabels
          />

          {canModerate && !showActions && (
            <Button size="sm" onClick={() => setShowActions(true)}>
              {t('moderation.review')}
            </Button>
          )}
        </div>
      </div>

      {showActions && (
        <div className="mt-4 space-y-4 rounded-md border bg-muted/30 p-4">
          <div className="space-y-1.5">
            <Label htmlFor={`points-${report.id}`}>
              {t('moderation.overridePoints')}
            </Label>
            <Input
              id={`points-${report.id}`}
              type="number"
              min={0}
              value={finalPoints}
              onChange={(e) => setFinalPoints(e.target.value)}
              placeholder={
                report.calculatedPoints?.toString() ??
                t('moderation.pointsPlaceholder')
              }
              className="max-w-[150px]"
            />
            <p className="text-xs text-muted-foreground">
              {t('moderation.overrideHint')}
            </p>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor={`comment-${report.id}`}>
              {t('moderation.comment')}
            </Label>
            <Textarea
              id={`comment-${report.id}`}
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder={t('moderation.commentPlaceholder')}
              rows={2}
            />
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}

          <div className="flex flex-wrap gap-2">
            <Button
              size="sm"
              onClick={() => handleModerate('APPROVED')}
              disabled={moderateReport.isPending}
            >
              <Check className="h-3 w-3" />
              {t('moderation.approve')}
            </Button>
            <Button
              size="sm"
              variant="secondary"
              onClick={() => handleModerate('CHANGES_REQUIRED')}
              disabled={moderateReport.isPending}
            >
              <MessageSquarePlus className="h-3 w-3" />
              {t('moderation.requestChanges')}
            </Button>
            <Button
              size="sm"
              variant="destructive"
              onClick={() => handleModerate('CLOSED')}
              disabled={moderateReport.isPending}
            >
              <X className="h-3 w-3" />
              {t('moderation.reject')}
            </Button>
            <Button size="sm" variant="ghost" onClick={resetForm}>
              {t('common.cancel')}
            </Button>
          </div>
        </div>
      )}

      {/* Comment history from audit log */}
      <CommentThread reportId={report.id} />
    </div>
  )
}
