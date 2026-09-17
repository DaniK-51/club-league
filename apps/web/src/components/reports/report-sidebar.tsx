import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Check,
  X,
  MessageSquarePlus,
  Send,
  Trash2,
  Save,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { StatusBadge } from '@/components/ui/status-badge'
import { ReportLinks } from '@/components/ui/report-links'
import { RuleConfigDisplay } from './rule-config-display'
import {
  useSubmitReport,
  useDeleteReport,
  useModerateReport,
} from '@/hooks/use-reports'
import { useUpdateReportData } from '@/hooks/use-report-data'
import { formatDate } from '@/lib/date-utils'
import { useAuthStore } from '@/store/auth.store'
import { ApiError } from '@/lib/types'
import type { ReportResponse, CriteriaRuleOut } from '@/lib/types'

interface ReportSidebarProps {
  report: ReportResponse
  rule: CriteriaRuleOut | undefined
  onNavigateBack: () => void
}

export function ReportSidebar({ report, rule, onNavigateBack }: ReportSidebarProps) {
  const { t } = useTranslation()
  const user = useAuthStore((s) => s.user)
  const submitReport = useSubmitReport()
  const deleteReport = useDeleteReport()
  const moderateReport = useModerateReport()
  const updateReportData = useUpdateReportData(report.id)

  const [comment, setComment] = useState('')
  const [finalPoints, setFinalPoints] = useState('')
  const [actionError, setActionError] = useState<string | null>(null)

  // Report data editing state
  const [reportData, setReportData] = useState<Record<string, unknown>>({})
  const [editingParams, setEditingParams] = useState(false)

  const isModerator = user?.role === 'MODERATOR'
  const isLeader = user?.role === 'CLUB_LEADER'

  const canSubmit =
    report.status === 'DRAFT' || report.status === 'CHANGES_REQUIRED'
  const canDelete = report.status === 'DRAFT'
  const canModerate =
    report.status === 'ON_MODERATION' || report.status === 'DISPUTED'
  const canEditParams =
    isModerator ||
    (isLeader && (report.status === 'DRAFT' || report.status === 'CHANGES_REQUIRED'))

  const handleModerate = (
    status: 'APPROVED' | 'CHANGES_REQUIRED' | 'CLOSED'
  ) => {
    setActionError(null)
    const needsComment =
      status === 'CHANGES_REQUIRED' ||
      (status === 'APPROVED' && finalPoints !== '')
    if (needsComment && !comment.trim()) {
      setActionError(t('moderation.commentRequired'))
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
        onSuccess: () => {
          setComment('')
          setFinalPoints('')
        },
        onError: (err) => {
          setActionError(
            err instanceof ApiError ? err.message : t('moderation.actionError')
          )
        },
      }
    )
  }

  const handleSaveParams = () => {
    setActionError(null)
    updateReportData.mutate(
      { reportData },
      {
        onSuccess: () => setEditingParams(false),
        onError: (err) => {
          setActionError(
            err instanceof ApiError ? err.message : t('report.saveParamsError')
          )
        },
      }
    )
  }

  return (
    <div className="space-y-6">
      {/* Status */}
      <SidebarSection title={t('report.status')}>
        <StatusBadge status={report.status} />
        {report.isOverdue && (
          <p className="mt-1 text-xs text-yellow-600">
            {t('report.overdueBadge')}
          </p>
        )}
      </SidebarSection>

      {/* Details */}
      <SidebarSection title={t('report.details')}>
        <dl className="space-y-2 text-sm">
          <div>
            <dt className="text-muted-foreground">{t('report.club')}</dt>
            <dd className="font-medium">{report.clubName}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">
              {t('report.activityDate')}
            </dt>
            <dd className="font-medium">
              {formatDate(report.activityDate)}
            </dd>
          </div>
        </dl>
      </SidebarSection>

      {/* Links */}
      <SidebarSection title={t('report.links')}>
        <ReportLinks links={report.links} />
      </SidebarSection>

      {/* Points */}
      <SidebarSection title={t('report.points')}>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">
              {t('moderation.calculated')}
            </span>
            <span className="font-medium">
              {report.calculatedPoints ?? '—'}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">
              {t('moderation.final')}
            </span>
            <span className="font-semibold text-primary">
              {report.finalPoints ?? '—'}
            </span>
          </div>
        </div>
      </SidebarSection>

      {/* Calculation Parameters */}
      {rule && (
        <SidebarSection title={t('report.calculationParams')}>
          {editingParams ? (
            <div className="space-y-3">
              <ParamEditor
                rule={rule}
                values={reportData}
                onChange={setReportData}
              />
              <div className="flex gap-2">
                <Button
                  size="sm"
                  onClick={handleSaveParams}
                  disabled={updateReportData.isPending}
                >
                  <Save className="h-3 w-3" />
                  {t('common.save')}
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setEditingParams(false)}
                >
                  {t('common.cancel')}
                </Button>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              <RuleConfigDisplay rule={rule} />
              {canEditParams && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setEditingParams(true)}
                >
                  {t('report.editParams')}
                </Button>
              )}
            </div>
          )}
        </SidebarSection>
      )}

      {/* Moderator: final points override */}
      {isModerator && canModerate && (
        <SidebarSection title={t('moderation.overridePoints')}>
          <Input
            type="number"
            min={0}
            value={finalPoints}
            onChange={(e) => setFinalPoints(e.target.value)}
            placeholder={
              report.calculatedPoints?.toString() ??
              t('moderation.pointsPlaceholder')
            }
          />
          <p className="mt-1 text-xs text-muted-foreground">
            {t('moderation.overrideHint')}
          </p>
        </SidebarSection>
      )}

      {/* Actions */}
      <SidebarSection title={t('report.actions')}>
        <div className="space-y-3">
          {/* Comment for moderation */}
          {isModerator && canModerate && (
            <div className="space-y-1.5">
              <Label htmlFor="actionComment" className="text-xs">
                {t('moderation.comment')}
              </Label>
              <Textarea
                id="actionComment"
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder={t('moderation.commentPlaceholder')}
                rows={2}
              />
            </div>
          )}

          {actionError && (
            <p className="text-xs text-destructive">{actionError}</p>
          )}

          {/* Moderator actions */}
          {isModerator && canModerate && (
            <div className="flex flex-col gap-2">
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
            </div>
          )}

          {/* Leader actions */}
          {isLeader && canSubmit && (
            <Button
              size="sm"
              className="w-full"
              onClick={() => submitReport.mutate(report.id)}
              disabled={submitReport.isPending}
            >
              <Send className="h-3 w-3" />
              {t('report.submit')}
            </Button>
          )}
          {isLeader && canDelete && (
            <Button
              size="sm"
              variant="destructive"
              className="w-full"
              onClick={() => {
                deleteReport.mutate(report.id, {
                  onSuccess: onNavigateBack,
                })
              }}
              disabled={deleteReport.isPending}
            >
              <Trash2 className="h-3 w-3" />
              {t('common.delete')}
            </Button>
          )}

          {/* Read-only notice */}
          {((isLeader && !canSubmit) ||
            (isModerator && !canModerate)) && (
            <p className="text-xs text-muted-foreground">
              {t('report.readOnlyForStatus', {
                status: t(`report.status.${report.status}`),
              })}
            </p>
          )}
        </div>
      </SidebarSection>
    </div>
  )
}

function SidebarSection({
  title,
  children,
}: {
  title: string
  children: React.ReactNode
}) {
  return (
    <div className="rounded-md border">
      <div className="border-b bg-muted/50 px-3 py-2">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {title}
        </h3>
      </div>
      <div className="p-3">{children}</div>
    </div>
  )
}

function ParamEditor({
  rule,
  values,
  onChange,
}: {
  rule: CriteriaRuleOut
  values: Record<string, unknown>
  onChange: (v: Record<string, unknown>) => void
}) {
  const { t } = useTranslation()
  const config = rule.config as Record<string, unknown>

  const setField = (key: string, value: unknown) => {
    onChange({ ...values, [key]: value })
  }

  const fieldDefs = getFieldDefs(rule.ruleType, config)

  return (
    <div className="space-y-2">
      {fieldDefs.map((field) => (
        <div key={field.key}>
          <Label className="text-xs">{t(field.labelKey)}</Label>
          {field.type === 'select' ? (
            <select
              value={(values[field.key] as string) ?? ''}
              onChange={(e) => setField(field.key, e.target.value)}
              className="mt-1 flex h-8 w-full rounded-md border border-input bg-transparent px-2 text-sm"
            >
              <option value="">—</option>
              {field.options?.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {t(opt.labelKey, opt.value)}
                </option>
              ))}
            </select>
          ) : (
            <Input
              type="number"
              value={(values[field.key] as number) ?? ''}
              onChange={(e) => setField(field.key, Number(e.target.value))}
              min={field.min}
              className="mt-1 h-8"
            />
          )}
        </div>
      ))}
    </div>
  )
}

interface FieldDef {
  key: string
  labelKey: string
  type: 'number' | 'select'
  min?: number
  options?: { value: string; labelKey: string }[]
}

function getFieldDefs(
  ruleType: string,
  config: Record<string, unknown>
): FieldDef[] {
  const levels = (config.levels as Record<string, number>) ?? {}

  switch (ruleType) {
    case 'tiered':
    case 'tiered_with_bonus':
      return [
        {
          key: (config.count_field as string) ?? 'count',
          labelKey: 'report.fields.count',
          type: 'number',
          min: 0,
        },
      ]
    case 'scale':
    case 'scale_with_frequency_limit':
    case 'scale_with_league_bonus':
      return [
        {
          key: (config.level_field as string) ?? 'level',
          labelKey: 'report.fields.level',
          type: 'select',
          options: Object.keys(levels).map((k) => ({
            value: k,
            labelKey: `report.levels.${k}`,
          })),
        },
      ]
    case 'binary':
    case 'binary_with_monthly_cap':
    case 'binary_scale': {
      const options =
        (config.options as Record<string, number>) ??
        Object.fromEntries(
          Object.entries(config).filter(
            ([k, v]) => typeof v === 'number' && k !== 'monthly_cap'
          )
        )
      return [
        {
          key: (config.variant_field as string) ?? 'variant',
          labelKey: 'report.fields.variant',
          type: 'select',
          options: Object.keys(options).map((k) => ({
            value: k,
            labelKey: `report.variants.${k}`,
          })),
        },
      ]
    }
    case 'discretionary':
      return [
        {
          key: (config.points_field as string) ?? 'points',
          labelKey: 'report.fields.points',
          type: 'number',
          min: (config.min as number) ?? 0,
        },
      ]
    case 'per_person_per_month': {
      const hasTrainers = config.per_trainer_per_month != null
      return [
        {
          key: hasTrainers
            ? ((config.trainers_field as string) ?? 'trainers')
            : ((config.leaders_field as string) ?? 'leaders'),
          labelKey: hasTrainers
            ? 'report.fields.trainers'
            : 'report.fields.leaders',
          type: 'number',
          min: 1,
        },
      ]
    }
    case 'per_unit_with_bonus':
      return [
        {
          key: (config.partners_field as string) ?? 'partners',
          labelKey: 'report.fields.partners',
          type: 'number',
          min: 1,
        },
      ]
    default:
      return []
  }
}
