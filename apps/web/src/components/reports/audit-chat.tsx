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
      <div className="relative">
        <div className="space-y-0">
          {comments?.map((entry) => (
            <TimelineItem key={entry.id} entry={entry} />
          ))}
        </div>
      </div>

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
  return isSystem ? <SystemEvent entry={entry} /> : <CommentCard entry={entry} />
}

function SystemEvent({ entry }: { entry: CommentEntry }) {
  const { t } = useTranslation()
  const icon = ACTION_ICONS[entry.action] ?? ACTION_ICONS.comment
  const dd = (entry.displayData ?? {}) as Record<string, unknown>

  // Render different detail based on action type
  const renderDetail = (): { detail: React.ReactNode; reason: string | null } => {
    switch (entry.action) {
      case 'created': {
        const pts = dd.calculated_points
        return {
          detail: (
            <>
              {typeof pts === 'number' && pts > 0 && (
                <span className="text-muted-foreground">
                  — {pts} {t('report.pointsUnit')}
                </span>
              )}
            </>
          ),
          reason: null,
        }
      }

      case 'status_changed': {
        const oldS = dd.old_status ? String(dd.old_status) : null
        const newS = dd.new_status ? String(dd.new_status) : null
        const finalPts = dd.final_points
        const modComment = dd.moderation_comment
        const reason = entry.oldValue && typeof entry.oldValue === 'object'
          ? String((entry.oldValue as Record<string, unknown>).reason ?? '')
          : null

        if (!oldS || !newS) {
          return { detail: null, reason: null }
        }

        const fromLabel = t(`report.status.${oldS}` as string, oldS)
        const toLabel = t(`report.status.${newS}` as string, newS)

        return {
          detail: (
            <>
              <span className="font-medium">
                {fromLabel} → {toLabel}
              </span>
              {typeof finalPts === 'number' && (
                <span className="ml-2 text-muted-foreground">
                  ({finalPts} {t('report.pointsUnit')})
                </span>
              )}
            </>
          ),
          reason: (modComment ? String(modComment) : null) ?? (reason || null),
        }
      }

      case 'points_updated': {
        const oldP = dd.old_points != null ? String(dd.old_points) : '—'
        const newP = dd.new_points != null ? String(dd.new_points) : '—'
        return {
          detail: (
            <span className="font-medium">
              {oldP} → {newP} {t('report.pointsUnit')}
            </span>
          ),
          reason: null,
        }
      }

      case 'calculation_updated': {
        const oldM = dd.old_method ? String(dd.old_method) : null
        const newM = dd.new_method ? String(dd.new_method) : null
        const manualPts = dd.manual_points != null ? String(dd.manual_points) : null
        if (!oldM && !newM) return { detail: null, reason: null }

        const fromM = oldM ? t(`moderation.calcModes.${oldM}` as string, oldM) : '—'
        const toM = newM ? t(`moderation.calcModes.${newM}` as string, newM) : '—'

        return {
          detail: (
            <>
              <span className="font-medium">
                {fromM} → {toM}
              </span>
              {newM === 'manual' && manualPts != null && (
                <span className="ml-2 text-muted-foreground">
                  ({manualPts} {t('report.pointsUnit')})
                </span>
              )}
            </>
          ),
          reason: null,
        }
      }

      case 'updated': {
        const oldPts = dd.old_calculated_points != null ? String(dd.old_calculated_points) : null
        const newPts = dd.new_calculated_points != null ? String(dd.new_calculated_points) : null
        if (oldPts || newPts) {
          return {
            detail: (
              <span className="text-muted-foreground">
                — {t('report.pointsUnit')}: {oldPts ?? '—'} → {newPts ?? '—'}
              </span>
            ),
            reason: null,
          }
        }
        return {
          detail: <span className="text-muted-foreground">— {t('report.paramsUpdated')}</span>,
          reason: null,
        }
      }

      case 'deleted':
        return { detail: null, reason: null }

      case 'sudo_action': {
        return {
          detail: null,
          reason: entry.body && entry.body !== entry.action ? entry.body : null,
        }
      }

      default:
        return {
          detail: entry.body && entry.body !== entry.action
            ? <span className="text-muted-foreground">— {entry.body}</span>
            : null,
          reason: null,
        }
    }
  }

  const { detail, reason } = renderDetail()

  // Action label — short description
  const actionLabel = t(`audit.actions.${entry.action}`, entry.action)

  return (
    <>
      <div className="flex items-center gap-2 py-2">
        <span className="flex h-5 w-5 shrink-0 items-center justify-center">
          {icon}
        </span>
        <div className="flex min-w-0 flex-1 flex-wrap items-baseline gap-x-2 gap-y-0.5 text-sm">
          <span className="font-medium">{entry.authorName}</span>
          <span className="text-muted-foreground">{actionLabel}</span>
          {detail}
        </div>
        <span className="shrink-0 text-xs text-muted-foreground">
          {formatDateTime(entry.createdAt)}
        </span>
      </div>

      {/* Reason block — separate below */}
      {reason && (
        <div className="mb-2 ml-7 rounded-md border-l-2 border-muted bg-muted/30 px-3 py-2">
          <div className="mb-1 text-xs text-muted-foreground">
            {t('moderation.reasonLabel')}
          </div>
          <p className="text-sm">{reason}</p>
        </div>
      )}
    </>
  )
}

function CommentCard({ entry }: { entry: CommentEntry }) {
  return (
    <div className="my-4 rounded-md border">
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
      <div className="px-4 py-3">
        <p className="whitespace-pre-wrap text-sm">{entry.body}</p>
      </div>
    </div>
  )
}
