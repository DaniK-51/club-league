import { useTranslation } from 'react-i18next'
import { useReportComments } from '@/hooks/use-moderation'
import { formatDate } from '@/lib/date-utils'

interface CommentThreadProps {
  reportId: string
}

export function CommentThread({ reportId }: CommentThreadProps) {
  const { t } = useTranslation()
  const { data: comments, isLoading } = useReportComments(reportId)

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">{t('common.loading')}</p>
  }

  if (!comments?.length) {
    return null
  }

  return (
    <div className="mt-3 space-y-2">
      <p className="text-xs font-medium text-muted-foreground">
        {t('moderation.history')}
      </p>
      {comments.map((entry) => (
        <div
          key={entry.id}
          className="rounded-md border-l-2 border-muted bg-muted/30 px-3 py-2 text-sm"
        >
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span className="font-medium">{entry.authorName}</span>
            <span>{entry.authorRole}</span>
            <span>·</span>
            <span>{formatDate(entry.createdAt)}</span>
            <span>·</span>
            <span>{t(`moderation.actions.${entry.action}`, entry.action)}</span>
          </div>
          {entry.comment && (
            <p className="mt-1">{entry.comment}</p>
          )}
        </div>
      ))}
    </div>
  )
}
