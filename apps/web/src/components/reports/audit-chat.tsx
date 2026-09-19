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

/**
 * System event with caption + details pattern.
 * caption — single line: "Author did something — key info"
 * details — block below with structured content (not always "reason")
 */
function SystemEvent({ entry }: { entry: CommentEntry }) {
  const { t } = useTranslation()
  const icon = ACTION_ICONS[entry.action] ?? ACTION_ICONS.comment
  const dd = (entry.displayData ?? {}) as Record<string, unknown>

  const { caption, details } = renderSystemEvent(entry.action, dd, t, entry.body)

  return (
    <>
      {/* Caption line */}
      <div className="flex items-center gap-2 py-2">
        <span className="flex h-5 w-5 shrink-0 items-center justify-center">
          {icon}
        </span>
        <div className="flex min-w-0 flex-1 flex-wrap items-baseline gap-x-2 text-sm">
          <span className="font-medium">{entry.authorName}</span>
          <span className="text-muted-foreground">{caption}</span>
        </div>
        <span className="shrink-0 text-xs text-muted-foreground">
          {formatDateTime(entry.createdAt)}
        </span>
      </div>

      {/* Details block */}
      {details.length > 0 && (
        <div className="mb-2 ml-7 space-y-1 rounded-md border-l-2 border-muted bg-muted/20 px-3 py-2">
          {details.map((d, i) => (
            <DetailRow key={i} {...d} />
          ))}
        </div>
      )}
    </>
  )
}

interface DetailRow {
  label?: string
  value: string
  mono?: boolean
}

function DetailRow({ label, value, mono }: DetailRow) {
  return (
    <div className="flex items-baseline gap-2 text-sm">
      {label && (
        <span className="shrink-0 text-xs text-muted-foreground">
          {label}
        </span>
      )}
      <span className={cn('min-w-0', mono && 'font-mono text-xs')}>
        {value}
      </span>
    </div>
  )
}

type TranslateFn = ReturnType<typeof useTranslation>['t']

function renderSystemEvent(
  action: string,
  dd: Record<string, unknown>,
  t: TranslateFn,
  body?: string
): { caption: string; details: DetailRow[] } {
  const details: DetailRow[] = []

  const str = (v: unknown): string | null =>
    v != null && v !== '' ? String(v) : null

  const statusLabel = (v: unknown): string | null => {
    const s = str(v)
    return s ? t(`report.status.${s}`, s) : null
  }

  const methodLabel = (v: unknown): string | null => {
    const m = str(v)
    return m ? t(`moderation.calcModes.${m}`, m) : null
  }

  const points = (v: unknown): string | null =>
    v != null ? `${String(v)} ${t('report.pointsUnit')}` : null

  const formatParams = (data: unknown): string | null => {
    if (!data || typeof data !== 'object') return null
    const entries = Object.entries(data as Record<string, unknown>)
      .filter(([, v]) => v != null && v !== '')
    if (entries.length === 0) return null
    return entries.map(([k, v]) => `${k}: ${String(v)}`).join(', ')
  }

  const actionLabel = t(`audit.actions.${action}`, action)

  switch (action) {
    case 'created': {
      const pts = points(dd.calculatedPoints)
      const params = formatParams(dd.reportData)
      const links = dd.links
      const linkList = Array.isArray(links)
        ? links
            .map((l) => (l && typeof l === 'object' && 'domain' in l ? String(l.domain) : null))
            .filter(Boolean)
            .join(', ')
        : null
      const parts = [pts, params, linkList].filter(Boolean)
      const caption = parts.length > 0
        ? `${actionLabel} — ${parts.join(' — ')}`
        : actionLabel
      return { caption, details }
    }

    case 'status_changed': {
      const oldS = statusLabel(dd.oldStatus)
      const newS = statusLabel(dd.newStatus)
      const statusPart = oldS && newS ? `${oldS} → ${newS}` : null
      const caption = statusPart
        ? `${actionLabel} — ${statusPart}`
        : actionLabel
      const calcPts = points(dd.calculatedPoints)
      if (calcPts) details.push({ label: t('moderation.calculated'), value: calcPts })
      const finPts = points(dd.finalPoints)
      if (finPts) details.push({ label: t('moderation.final'), value: finPts })
      const method = methodLabel(dd.calculationMethod)
      const manualPts = points(dd.manualPoints)
      if (method === t('moderation.calcModes.manual') && manualPts) {
        details.push({ label: t('moderation.manualPoints'), value: manualPts })
      }
      const modComment = str(dd.moderationComment)
      if (modComment) details.push({ label: t('moderation.reasonLabel'), value: modComment })
      return { caption, details }
    }

    case 'points_updated': {
      const oldP = str(dd.oldPoints) ?? '—'
      const newP = str(dd.newPoints) ?? '—'
      const caption = `${actionLabel} — ${oldP} → ${newP} ${t('report.pointsUnit')}`
      const method = methodLabel(dd.calculationMethod)
      if (method) details.push({ label: t('moderation.calcMethod'), value: method })
      const modComment = str(dd.moderationComment)
      if (modComment) details.push({ label: t('moderation.reasonLabel'), value: modComment })
      return { caption, details }
    }

    case 'calculation_updated': {
      const oldM = methodLabel(dd.oldMethod)
      const newM = methodLabel(dd.newMethod)
      const methodPart = oldM && newM ? `${oldM} → ${newM}` : newM ?? oldM
      const manualPts = points(dd.manualPoints)
      const caption = methodPart
        ? `${actionLabel} — ${methodPart}${manualPts ? ` (${manualPts})` : ''}`
        : actionLabel
      const reason = str(dd.reason)
      if (reason) details.push({ label: t('moderation.reasonLabel'), value: reason })
      return { caption, details }
    }

    case 'updated': {
      const oldPts = str(dd.oldCalculatedPoints)
      const newPts = str(dd.newCalculatedPoints)
      const ptsPart = oldPts && newPts ? `${oldPts} → ${newPts}` : null
      const caption = ptsPart
        ? `${actionLabel} — ${t('report.points')}: ${ptsPart}`
        : actionLabel
      // Show changes from backend: [{ field, old, new }]
      const changes = dd.changes
      if (Array.isArray(changes)) {
        for (const change of changes) {
          if (!change || typeof change !== 'object') continue
          const field = 'field' in change ? String(change.field) : null
          const oldVal = 'old' in change ? change.old : null
          const newVal = 'new' in change ? change.new : null

          if (field === 'reportData') {
            const oldP = formatParams(oldVal)
            const newP = formatParams(newVal)
            if (oldP) details.push({ label: `${t('report.parameters')} (${t('common.old', 'было')})`, value: oldP })
            if (newP) details.push({ label: `${t('report.parameters')} (${t('common.new', 'стало')})`, value: newP })
          } else if (field === 'links') {
            const oldLinks = Array.isArray(oldVal)
              ? oldVal.map((l) => String(l)).join(', ')
              : null
            const newLinks = Array.isArray(newVal)
              ? newVal.map((l) => String(l)).join(', ')
              : null
            if (oldLinks) details.push({ label: `${t('report.links')} (${t('common.old', 'было')})`, value: oldLinks })
            if (newLinks) details.push({ label: `${t('report.links')} (${t('common.new', 'стало')})`, value: newLinks })
          } else if (field === 'activityDate') {
            if (oldVal) details.push({ label: `${t('report.activityDate')} (${t('common.old', 'было')})`, value: String(oldVal) })
            if (newVal) details.push({ label: `${t('report.activityDate')} (${t('common.new', 'стало')})`, value: String(newVal) })
          }
        }
      }
      return { caption, details }
    }

    case 'deleted': {
      return { caption: actionLabel, details }
    }

    case 'sudo_action': {
      const reason = str(dd.reason) ?? (body && body !== action ? body : null)
      if (reason) details.push({ label: t('moderation.reasonLabel'), value: reason })
      return { caption: actionLabel, details }
    }

    default: {
      return { caption: actionLabel, details }
    }
  }
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
