import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Check, X, MessageSquarePlus, AlertTriangle, ExternalLink } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { useModerateReport } from '@/hooks/use-moderation'
import { formatDate } from '@/lib/date-utils'
import { ApiError, type ReportResponse } from '@/lib/types'
import { cn } from '@/lib/utils'

interface ModerationCardProps {
  report: ReportResponse
}

export function ModerationCard({ report }: ModerationCardProps) {
  const { t } = useTranslation()
  const moderateReport = useModerateReport()

  const [showActions, setShowActions] = useState(false)
  const [comment, setComment] = useState('')
  const [finalPoints, setFinalPoints] = useState<string>('')
  const [error, setError] = useState<string | null>(null)

  const needsComment = (status: string) => {
    if (status === 'CHANGES_REQUIRED') return true
    if (status === 'APPROVED' && finalPoints !== '') return true
    return false
  }

  const canModerate = report.status === 'ON_MODERATION' || report.status === 'DISPUTED'

  const handleModerate = (status: 'APPROVED' | 'CHANGES_REQUIRED' | 'CLOSED') => {
    setError(null)

    if (needsComment(status) && !comment.trim()) {
      setError(t('moderation.commentRequired'))
      return
    }

    const dto = {
      status,
      comment: comment.trim(),
      ...(finalPoints !== '' ? { finalPoints: Number(finalPoints) } : {}),
    }

    moderateReport.mutate(
      { id: report.id, dto },
      {
        onSuccess: () => {
          setShowActions(false)
          setComment('')
          setFinalPoints('')
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
        'rounded-md border p-4',
        report.isOverdue && 'border-yellow-300 bg-yellow-50/50'
      )}
    >
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="font-semibold">{report.criteriaCode}</span>
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
          <div className="flex flex-wrap gap-1">
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
        </div>

        <div className="flex items-center gap-3">
          <div className="text-right">
            {report.calculatedPoints != null && (
              <p className="text-sm text-muted-foreground">
                {t('moderation.calculated')}:{' '}
                <span className="font-medium">{report.calculatedPoints}</span>
              </p>
            )}
            {report.finalPoints != null && (
              <p className="text-sm font-semibold">
                {t('moderation.final')}:{' '}
                <span className="text-primary">{report.finalPoints}</span>
              </p>
            )}
          </div>

          {canModerate && !showActions && (
            <Button size="sm" onClick={() => setShowActions(true)}>
              {t('moderation.review')}
            </Button>
          )}
        </div>
      </div>

      {/* Moderation actions panel */}
      {showActions && (
        <div className="mt-4 space-y-4 rounded-md border bg-muted/30 p-4">
          {/* Points override */}
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

          {/* Comment */}
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

          {/* Action buttons */}
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
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                setShowActions(false)
                setComment('')
                setFinalPoints('')
                setError(null)
              }}
            >
              {t('common.cancel')}
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

function StatusBadge({ status }: { status: ReportResponse['status'] }) {
  const { t } = useTranslation()

  const colors: Record<string, string> = {
    DRAFT: 'bg-muted text-muted-foreground',
    ON_MODERATION: 'bg-blue-100 text-blue-800',
    CHANGES_REQUIRED: 'bg-yellow-100 text-yellow-800',
    APPROVED: 'bg-green-100 text-green-800',
    DISPUTED: 'bg-orange-100 text-orange-800',
    COMPLETED: 'bg-emerald-100 text-emerald-800',
    CLOSED: 'bg-red-100 text-red-800',
    ARCHIVED: 'bg-gray-100 text-gray-800',
  }

  return (
    <span
      className={cn(
        'rounded-full px-2 py-0.5 text-xs font-medium',
        colors[status]
      )}
    >
      {t(`report.status.${status}`)}
    </span>
  )
}
