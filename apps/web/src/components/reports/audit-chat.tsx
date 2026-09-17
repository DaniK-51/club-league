import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  CircleDot,
  XCircle,
  AlertCircle,
  MessageSquare,
  Settings,
  Pencil,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { useReportComments } from '@/hooks/use-reports'
import { usePostComment } from '@/hooks/use-comments'
import { formatDateTime } from '@/lib/date-utils'
import { useAuthStore } from '@/store/auth.store'
import { cn } from '@/lib/utils'
import type { CommentEntry } from '@/lib/types'

// System events — compact GitHub-style timeline items
const SYSTEM_ACTIONS = new Set([
  'created',
  'status_changed',
  'points_updated',
  'updated',
  'deleted',
  'sudo_action',
  'calculation_updated',
])

const ACTION_ICONS: Record<string, React.ReactNode> = {
  created: <CircleDot className="h-3.5 w-3.5 text-green-600" />,
  status_changed: <AlertCircle className="h-3.5 w-3.5 text-blue-600" />,
  points_updated: <Pencil className="h-3.5 w-3.5 text-purple-600" />,
  updated: <Pencil className="h-3.5 w-3.5 text-yellow-600" />,
  deleted: <XCircle className="h-3.5 w-3.5 text-red-600" />,
  sudo_action: <Settings className="h-3.5 w-3.5 text-orange-600" />,
  calculation_updated: <Pencil className="h-3.5 w-3.5 text-purple-600" />,
  comment: <MessageSquare className="h-3.5 w-3.5 text-muted-foreground" />,
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
    <div>
      {/* Timeline */}
      <div className="relative">
        <div className="space-y-0">
          {comments?.map((entry) => (
            <TimelineItem key={entry.id} entry={entry} />
          ))}
        </div>
      </div>

      {/* Comment input — GitHub style */}
      {isAuthenticated && (
        <div className="mt-6 rounded-md border">
          <div className="border-b bg-muted/50 px-4 py-2">
            <div className="flex items-center gap-2">
              <Avatar name={user.name} />
              <span className="text-sm font-medium">{user.name}</span>
            </div>
          </div>
          <div className="p-4">
            <Textarea
              value={newComment}
              onChange={(e) => setNewComment(e.target.value)}
              placeholder={t('report.commentPlaceholder')}
              rows={3}
              className="min-h-[80px]"
            />
            <div className="mt-2 flex justify-end">
              <Button
                size="sm"
                onClick={handleSubmit}
                disabled={!newComment.trim() || postComment.isPending}
              >
                {t('report.commentSubmit')}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function Avatar({ name, size = 'sm' }: { name: string; size?: 'sm' | 'md' }) {
  return (
    <div
      className={cn(
        'flex shrink-0 items-center justify-center rounded-full bg-muted font-medium',
        size === 'sm' ? 'h-6 w-6 text-xs' : 'h-8 w-8 text-sm'
      )}
    >
      {name?.charAt(0) ?? '?'}
    </div>
  )
}

function TimelineItem({ entry }: { entry: CommentEntry }) {
  const isSystem = SYSTEM_ACTIONS.has(entry.action)

  if (isSystem) {
    // If system event has a message, show status change + reason separately
    const hasReason =
      !!entry.body &&
      entry.body !== entry.action &&
      !entry.body.startsWith('status →') &&
      !entry.body.startsWith('final_points →')

    return (
      <>
        <SystemEvent entry={entry} hideBody={hasReason} />
        {hasReason && <ReasonBlock entry={entry} />}
      </>
    )
  }
  return <CommentCard entry={entry} />
}

// GitHub-style compact system event
function SystemEvent({ entry, hideBody }: { entry: CommentEntry; hideBody?: boolean }) {
  const { t } = useTranslation()
  const icon = ACTION_ICONS[entry.action] ?? ACTION_ICONS.comment

  // Parse body into human-readable format
  const getDetail = (): string | null => {
    const body = entry.body
    if (!body || body === entry.action) return null

    // Status change: "status → APPROVED" or "ON_MODERATION → APPROVED"
    const statusMatch = body.match(/(?:status\s*→\s*)?([A-Z_]+)\s*→\s*([A-Z_]+)/)
    if (statusMatch?.[1] && statusMatch[2]) {
      const from = t(`report.status.${statusMatch[1]}` as string, statusMatch[1])
      const to = t(`report.status.${statusMatch[2]}` as string, statusMatch[2])
      return `${from} → ${to}`
    }

    // Single status: "status → APPROVED"
    const singleStatus = body.match(/status\s*→\s*([A-Z_]+)/)
    if (singleStatus?.[1]) {
      return t(`report.status.${singleStatus[1]}` as string, singleStatus[1])
    }

    // Points: "final_points → 350"
    const pointsMatch = body.match(/(?:final|calculated)_points\s*→\s*(\d+)/)
    if (pointsMatch?.[1]) {
      return `${pointsMatch[1]} ${t('report.pointsUnit')}`
    }

    // Calculation method
    const calcMatch = body.match(/calculation_method\s*→\s*(\w+)/)
    if (calcMatch?.[1]) {
      return t(`moderation.calcModes.${calcMatch[1]}` as string, calcMatch[1])
    }

    return body
  }

  const detail = getDetail()

  return (
    <div className="flex items-center gap-2 py-2">
      <span className="flex h-5 w-5 shrink-0 items-center justify-center">
        {icon}
      </span>
      <div className="flex min-w-0 flex-1 items-baseline gap-2 text-sm">
        <span className="font-medium">{entry.authorName}</span>
        <span className="text-muted-foreground">
          {t(`moderation.actions.${entry.action}`, entry.action)}
        </span>
        {!hideBody && detail && (
          <span className="text-muted-foreground">
            {detail}
          </span>
        )}
      </div>
      <span className="shrink-0 text-xs text-muted-foreground">
        {formatDateTime(entry.createdAt)}
      </span>
    </div>
  )
}

// Reason block — shown below status change
function ReasonBlock({ entry }: { entry: CommentEntry }) {
  const { t } = useTranslation()

  return (
    <div className="mb-2 ml-7 rounded-md border-l-2 border-muted bg-muted/30 px-3 py-2">
      <div className="mb-1 text-xs text-muted-foreground">
        {t('moderation.reasonLabel')}
      </div>
      <p className="text-sm">{entry.body}</p>
    </div>
  )
}

// GitHub-style comment card
function CommentCard({ entry }: { entry: CommentEntry }) {
  return (
    <div className="my-4 rounded-md border">
      {/* Header */}
      <div className="flex items-center justify-between border-b bg-muted/50 px-4 py-2">
        <div className="flex items-center gap-2">
          <Avatar name={entry.authorName} size="md" />
          <span className="text-sm font-medium">{entry.authorName}</span>
          <span className="text-xs text-muted-foreground">
            {formatDateTime(entry.createdAt)}
          </span>
        </div>
        <span className="flex h-5 w-5 items-center justify-center rounded-full bg-muted">
          {ACTION_ICONS.comment}
        </span>
      </div>

      {/* Body */}
      <div className="px-4 py-3">
        <p className="whitespace-pre-wrap text-sm">{entry.body}</p>
      </div>
    </div>
  )
}
