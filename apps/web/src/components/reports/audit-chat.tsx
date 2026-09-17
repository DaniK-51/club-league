import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Send } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { useReportComments } from '@/hooks/use-reports'
import { usePostComment } from '@/hooks/use-comments'
import { formatDate } from '@/lib/date-utils'
import { useAuthStore } from '@/store/auth.store'
import { cn } from '@/lib/utils'
import type { CommentEntry } from '@/lib/types'

const ACTION_COLORS: Record<string, string> = {
  created: 'bg-green-100 text-green-800',
  status_changed: 'bg-blue-100 text-blue-800',
  points_updated: 'bg-purple-100 text-purple-800',
  updated: 'bg-yellow-100 text-yellow-800',
  deleted: 'bg-red-100 text-red-800',
  sudo_action: 'bg-orange-100 text-orange-800',
  comment: 'bg-muted text-muted-foreground',
}

interface AuditChatProps {
  reportId: string
}

export function AuditChat({ reportId }: AuditChatProps) {
  const { t } = useTranslation()
  const user = useAuthStore((s) => s.user)
  const { data: comments, isLoading } = useReportComments(reportId)
  const postComment = usePostComment(reportId)
  const [newComment, setNewComment] = useState('')

  const isAuthenticated = !!user

  const handleSubmit = () => {
    if (!newComment.trim()) return
    postComment.mutate(newComment.trim(), {
      onSuccess: () => setNewComment(''),
    })
  }

  if (isLoading) {
    return <p className="text-muted-foreground">{t('common.loading')}</p>
  }

  return (
    <div className="flex flex-col space-y-0">
      {/* Timeline */}
      <div className="relative">
        {/* Vertical line */}
        <div className="absolute left-4 top-0 bottom-0 w-px bg-border" />

        <div className="space-y-0">
          {comments?.map((entry) => (
            <TimelineEntry key={entry.id} entry={entry} />
          ))}
        </div>
      </div>

      {/* Comment input */}
      {isAuthenticated && (
        <div className="relative mt-4">
          <div className="absolute left-4 -top-4 h-4 w-px bg-border" />
          <div className="ml-10 rounded-md border bg-background p-4">
            <div className="mb-2 flex items-center gap-2">
              <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-xs text-primary-foreground">
                {user.name?.charAt(0) ?? '?'}
              </div>
              <span className="text-sm font-medium">{user.name}</span>
            </div>
            <Textarea
              value={newComment}
              onChange={(e) => setNewComment(e.target.value)}
              placeholder={t('report.commentPlaceholder')}
              rows={3}
            />
            <div className="mt-2 flex justify-end">
              <Button
                size="sm"
                onClick={handleSubmit}
                disabled={!newComment.trim() || postComment.isPending}
              >
                <Send className="h-3 w-3" />
                {t('report.commentSubmit')}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function TimelineEntry({ entry }: { entry: CommentEntry }) {
  const { t } = useTranslation()
  const actionColor = ACTION_COLORS[entry.action] ?? ACTION_COLORS.comment

  return (
    <div className="relative flex gap-3 pb-6">
      {/* Avatar */}
      <div className="relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border bg-background">
        <span className="text-xs font-medium">
          {entry.authorName?.charAt(0) ?? '?'}
        </span>
      </div>

      {/* Content */}
      <div className="min-w-0 flex-1">
        <div className="rounded-md border bg-background">
          {/* Header */}
          <div className="flex flex-wrap items-center gap-2 border-b px-3 py-2">
            <span className="text-sm font-medium">{entry.authorName}</span>
            <span className="text-xs text-muted-foreground">
              {entry.authorRole}
            </span>
            <span className="text-xs text-muted-foreground">·</span>
            <span className="text-xs text-muted-foreground">
              {formatDate(entry.createdAt)}
            </span>
            <span
              className={cn(
                'rounded-full px-2 py-0.5 text-xs font-medium',
                actionColor
              )}
            >
              {t(`moderation.actions.${entry.action}`, entry.action)}
            </span>
          </div>

          {/* Body */}
          <div className="px-3 py-2">
            <p className="whitespace-pre-wrap text-sm">{entry.body}</p>
          </div>
        </div>
      </div>
    </div>
  )
}
