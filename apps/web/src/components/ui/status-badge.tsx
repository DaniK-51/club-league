import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/utils'
import type { ReportStatus } from '@/lib/types'

const STATUS_COLORS: Record<ReportStatus, string> = {
  DRAFT: 'bg-muted text-muted-foreground',
  ON_MODERATION: 'bg-blue-100 text-blue-800',
  CHANGES_REQUIRED: 'bg-yellow-100 text-yellow-800',
  APPROVED: 'bg-green-100 text-green-800',
  DISPUTED: 'bg-orange-100 text-orange-800',
  COMPLETED: 'bg-emerald-100 text-emerald-800',
  CLOSED: 'bg-red-100 text-red-800',
  ARCHIVED: 'bg-gray-100 text-gray-800',
}

interface StatusBadgeProps {
  status: ReportStatus
  className?: string
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const { t } = useTranslation()

  return (
    <span
      className={cn(
        'rounded-full px-2 py-0.5 text-xs font-medium',
        STATUS_COLORS[status],
        className
      )}
    >
      {t(`report.status.${status}`)}
    </span>
  )
}
