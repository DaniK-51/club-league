import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Check,
  X,
  MessageSquarePlus,
  Send,
  Trash2,
  Save,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { StatusBadge } from '@/components/ui/status-badge'
import { ReportLinks } from '@/components/ui/report-links'
import {
  useSubmitReport,
  useDeleteReport,
  useModerateReport,
  useCompleteReport,
  useDisputeReport,
} from '@/hooks/use-reports'
import { useUpdateReportData } from '@/hooks/use-report-data'
import { useSetCalculation } from '@/hooks/use-calculation'
import { formatDate } from '@/lib/date-utils'
import { useAuthStore } from '@/store/auth.store'
import { ApiError } from '@/lib/types'
import type { ReportResponse, CriteriaRuleOut } from '@/lib/types'

const MODERATOR_EDIT_STATUSES = ['ON_MODERATION', 'DISPUTED', 'CHANGES_REQUIRED', 'APPROVED']
const LEADER_EDIT_STATUSES = ['DRAFT', 'CHANGES_REQUIRED']

interface ReportSidebarProps {
  report: ReportResponse
  rule: CriteriaRuleOut | undefined
  criteriaName?: string
  onNavigateBack: () => void
}

export function ReportSidebar({ report, rule, criteriaName, onNavigateBack }: ReportSidebarProps) {
  return (
    <ReportSidebarInner
      key={report.id}
      report={report}
      rule={rule}
      criteriaName={criteriaName}
      onNavigateBack={onNavigateBack}
    />
  )
}

function ReportSidebarInner({ report, rule, criteriaName, onNavigateBack }: ReportSidebarProps) {
  const { t } = useTranslation()
  const user = useAuthStore((s) => s.user)
  const submitReport = useSubmitReport()
  const deleteReport = useDeleteReport()
  const moderateReport = useModerateReport()
  const completeReport = useCompleteReport()
  const disputeReport = useDisputeReport()
  const updateReportData = useUpdateReportData(report.id)
  const setCalculation = useSetCalculation(report.id)

  const [comment, setComment] = useState('')
  const [disputeComment, setDisputeComment] = useState('')
  const [showDisputeForm, setShowDisputeForm] = useState(false)
  const [finalPoints, setFinalPoints] = useState('')
  const [actionError, setActionError] = useState<string | null>(null)

  // Result editing state
  const [editingResult, setEditingResult] = useState(false)
  const [calcMode, setCalcMode] = useState<'auto' | 'manual'>(
    report.finalPoints != null ? 'manual' : 'auto'
  )
  const [manualPoints, setManualPoints] = useState(
    report.finalPoints?.toString() ?? ''
  )
  const [calcReason, setCalcReason] = useState('')

  // Report data editing state — initialized from report on mount
  const [reportData, setReportData] = useState<Record<string, unknown>>(
    () => report.reportData ?? {}
  )
  const [editingParams, setEditingParams] = useState(false)

  const isModerator = user?.role === 'MODERATOR'
  const isLeader = user?.role === 'CLUB_LEADER'

  const canSubmit =
    report.status === 'DRAFT' || report.status === 'CHANGES_REQUIRED'
  const canDelete = report.status === 'DRAFT'
  const canModerate =
    report.status === 'ON_MODERATION' || report.status === 'DISPUTED'
  const canComplete = report.status === 'APPROVED'
  const canDispute = report.status === 'APPROVED'
  const canEditParams =
    (isModerator && MODERATOR_EDIT_STATUSES.includes(report.status)) ||
    (isLeader && LEADER_EDIT_STATUSES.includes(report.status))

  const handleModerate = (
    status: 'APPROVED' | 'CHANGES_REQUIRED' | 'CLOSED'
  ) => {
    setActionError(null)
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

  const handleSaveResult = () => {
    setActionError(null)
    setCalculation.mutate(
      {
        method: calcMode,
        ...(calcMode === 'manual' ? { manualPoints: Number(manualPoints) || 0 } : {}),
        ...(calcReason.trim() ? { reason: calcReason.trim() } : {}),
      },
      {
        onSuccess: () => {
          setEditingResult(false)
          setCalcReason('')
        },
        onError: (err) => {
          setActionError(
            err instanceof ApiError ? err.message : t('moderation.actionError')
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
        <div className="space-y-3">
          <div className="space-y-2 text-sm">
            {/* Calculated points — always shown */}
            <div className="flex justify-between">
              <span className="text-muted-foreground">
                {t('moderation.calculated')}
              </span>
              <span className="font-semibold">
                {report.calculatedPoints ?? '—'}
              </span>
            </div>

            {/* Calculation method */}
            <div className="flex justify-between text-xs">
              <span className="text-muted-foreground">
                {t('moderation.calcMethod')}
              </span>
              <span>
                {t(`moderation.calcModes.${report.calculationMethod ?? 'auto'}`)}
              </span>
            </div>

            {/* Manual points — when method is manual */}
            {report.calculationMethod === 'manual' && report.manualPoints != null && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">
                  {t('moderation.manualPoints')}
                </span>
                <span className="font-semibold text-orange-600">
                  {report.manualPoints}
                </span>
              </div>
            )}

            {/* Final points — only on late stages when set */}
            {report.finalPoints != null && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">
                  {t('moderation.final')}
                </span>
                <span className="font-semibold text-primary">
                  {report.finalPoints}
                </span>
              </div>
            )}
          </div>

          {/* Moderator: edit result */}
          {isModerator && canModerate && (
            <div className="space-y-2">
              {editingResult ? (
                <div className="space-y-2 rounded-md bg-muted/30 p-2">
                  <Label className="text-xs">
                    {t('moderation.calcMethod')}
                  </Label>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant={calcMode === 'auto' ? 'default' : 'outline'}
                      onClick={() => setCalcMode('auto')}
                    >
                      {t('moderation.calcModes.auto')}
                    </Button>
                    <Button
                      size="sm"
                      variant={calcMode === 'manual' ? 'default' : 'outline'}
                      onClick={() => setCalcMode('manual')}
                    >
                      {t('moderation.calcModes.manual')}
                    </Button>
                  </div>
                  {calcMode === 'manual' && (
                    <div className="space-y-1">
                      <Label className="text-xs">
                        {t('moderation.manualPoints')}
                      </Label>
                      <Input
                        type="number"
                        min={0}
                        value={manualPoints}
                        onChange={(e) => setManualPoints(e.target.value)}
                        placeholder={
                          report.calculatedPoints?.toString() ?? '0'
                        }
                        className="h-8"
                      />
                    </div>
                  )}
                  <div className="space-y-1">
                    <Label className="text-xs">
                      {t('moderation.reasonLabel')}
                    </Label>
                    <Textarea
                      value={calcReason}
                      onChange={(e) => setCalcReason(e.target.value)}
                      placeholder={t('moderation.reasonPlaceholder')}
                      rows={2}
                    />
                  </div>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      onClick={handleSaveResult}
                      disabled={setCalculation.isPending}
                    >
                      <Save className="h-3 w-3" />
                      {t('common.save')}
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => {
                        setEditingResult(false)
                        setCalcReason('')
                      }}
                    >
                      {t('common.cancel')}
                    </Button>
                  </div>
                </div>
              ) : (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setCalcMode(report.calculationMethod ?? 'auto')
                    setManualPoints(report.manualPoints?.toString() ?? '')
                    setEditingResult(true)
                  }}
                >
                  {t('report.editResult')}
                </Button>
              )}
            </div>
          )}
        </div>
      </SidebarSection>

      {/* Parameters */}
      {rule && (
        <SidebarSection title={t('report.parameters')}>
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
              {/* Criteria code + name */}
              <div>
                <span className="font-medium">{report.criteriaCode}</span>
                {criteriaName && (
                  <span className="ml-2 text-sm text-muted-foreground">
                    {criteriaName}
                  </span>
                )}
              </div>

              {/* Submitted values */}
              <SubmittedValues rule={rule} data={report.reportData ?? {}} />

              {/* Edit button — only when possible */}
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

          {/* Leader: Complete or Dispute when APPROVED */}
          {isLeader && canComplete && !showDisputeForm && (
            <div className="flex flex-col gap-2">
              <Button
                size="sm"
                className="w-full"
                onClick={() => completeReport.mutate(report.id)}
                disabled={completeReport.isPending}
              >
                <CheckCircle2 className="h-3 w-3" />
                {t('report.complete')}
              </Button>
              {canDispute && (
                <Button
                  size="sm"
                  variant="outline"
                  className="w-full"
                  onClick={() => setShowDisputeForm(true)}
                >
                  <AlertCircle className="h-3 w-3" />
                  {t('report.dispute')}
                </Button>
              )}
            </div>
          )}

          {/* Leader: Dispute form */}
          {isLeader && showDisputeForm && (
            <div className="space-y-2">
              <Label htmlFor="disputeComment" className="text-xs">
                {t('report.disputeComment')}
              </Label>
              <Textarea
                id="disputeComment"
                value={disputeComment}
                onChange={(e) => setDisputeComment(e.target.value)}
                placeholder={t('report.disputePlaceholder')}
                rows={3}
              />
              {actionError && (
                <p className="text-xs text-destructive">{actionError}</p>
              )}
              <div className="flex gap-2">
                <Button
                  size="sm"
                  onClick={() => {
                    if (!disputeComment.trim()) {
                      setActionError(t('report.disputeCommentRequired'))
                      return
                    }
                    disputeReport.mutate(
                      { id: report.id, comment: disputeComment.trim() },
                      {
                        onSuccess: () => {
                          setShowDisputeForm(false)
                          setDisputeComment('')
                        },
                        onError: (err) => {
                          setActionError(
                            err instanceof ApiError
                              ? err.message
                              : t('moderation.actionError')
                          )
                        },
                      }
                    )
                  }}
                  disabled={disputeReport.isPending}
                >
                  {t('report.disputeSubmit')}
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => {
                    setShowDisputeForm(false)
                    setDisputeComment('')
                    setActionError(null)
                  }}
                >
                  {t('common.cancel')}
                </Button>
              </div>
            </div>
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

function SubmittedValues({
  rule,
  data,
}: {
  rule: CriteriaRuleOut
  data: Record<string, unknown>
}) {
  const { t } = useTranslation()
  const config = rule.config as Record<string, unknown>
  const fieldDefs = getFieldDefs(rule.ruleType, config)

  const formatValue = (value: unknown, field: FieldDef): string => {
    if (field.type === 'select' && field.options) {
      const strVal = value === true ? 'true' : value === false ? 'false' : String(value)
      const opt = field.options.find((o) => o.value === strVal)
      return opt ? t(opt.labelKey, opt.value) : strVal
    }
    return String(value)
  }

  const entries = fieldDefs
    .map((field) => ({ field, value: data[field.key] }))
    .filter(({ value }) => value != null && value !== '')

  if (entries.length === 0) {
    return (
      <p className="text-xs text-muted-foreground">
        {t('report.noParams')}
      </p>
    )
  }

  return (
    <div className="space-y-1">
      {entries.map(({ field, value }) => (
        <div key={field.key} className="flex justify-between text-xs">
          <span className="text-muted-foreground">{t(field.labelKey)}</span>
          <span className="font-medium">{formatValue(value, field)}</span>
        </div>
      ))}
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
    // Convert boolean select values to actual booleans
    let processed = value
    if (value === 'true') processed = true
    if (value === 'false') processed = false
    onChange({ ...values, [key]: processed })
  }

  const fieldDefs = getFieldDefs(rule.ruleType, config)

  const getDisplayValue = (key: string, type: string): string => {
    const val = values[key]
    if (val == null) return ''
    if (type === 'select') {
      if (val === true) return 'true'
      if (val === false) return 'false'
      return String(val)
    }
    return String(val)
  }

  return (
    <div className="space-y-2">
      {fieldDefs.map((field) => (
        <div key={field.key}>
          <Label className="text-xs">{t(field.labelKey)}</Label>
          {field.type === 'select' ? (
            <select
              value={getDisplayValue(field.key, field.type)}
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
              value={getDisplayValue(field.key, field.type)}
              onChange={(e) => setField(field.key, e.target.value === '' ? undefined : Number(e.target.value))}
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
    case 'discretionary': {
      return [
        {
          key: (config.points_field as string) ?? 'points',
          labelKey: 'report.fields.pointsSimple',
          type: 'number',
          min: (config.min as number) ?? 0,
        },
      ]
    }
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
        {
          key: (config.cross_type_field as string) ?? 'cross_type',
          labelKey: 'report.fields.crossType',
          type: 'select',
          options: [
            { value: 'true', labelKey: 'common.yes' },
            { value: 'false', labelKey: 'common.no' },
          ],
        },
      ]
    case 'fixed_monthly_with_per_unit':
      return [
        {
          key: (config.extra_field as string) ?? 'extra_socials',
          labelKey: 'report.fields.extraSocials',
          type: 'number',
          min: 0,
        },
      ]
    case 'fixed_per_event_with_monthly_cap':
      return []
    case 'scale_with_conditional_bonus':
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
        {
          key: (config.focus_field as string) ?? 'full_club_focus',
          labelKey: 'report.fields.fullClubFocus',
          type: 'select',
          options: [
            { value: 'true', labelKey: 'common.yes' },
            { value: 'false', labelKey: 'common.no' },
          ],
        },
      ]
    case 'scale_split_mode':
    case 'scale_with_conditional_modifier': {
      const modeField = (config.mode_field as string) ?? 'mode'
      const levelField = (config.level_field as string) ?? 'level'
      // Levels depend on mode — show individual levels as options
      const individualLevels = (config.individual as Record<string, number>) ?? {}
      const teamLevels = (config.team as Record<string, number>) ?? {}
      const allLevelKeys = [...new Set([...Object.keys(individualLevels), ...Object.keys(teamLevels)])]
      const fields: FieldDef[] = [
        {
          key: modeField,
          labelKey: 'report.fields.mode',
          type: 'select',
          options: [
            { value: 'individual', labelKey: 'report.modes.individual' },
            { value: 'team', labelKey: 'report.modes.team' },
          ],
        },
        {
          key: levelField,
          labelKey: 'report.fields.level',
          type: 'select',
          options: allLevelKeys.map((k) => ({
            value: k,
            labelKey: `report.levels.${k}`,
          })),
        },
      ]
      if (ruleType === 'scale_with_conditional_modifier') {
        fields.push({
          key: (config.is_host_field as string) ?? 'is_host',
          labelKey: 'report.fields.isHost',
          type: 'select',
          options: [
            { value: 'true', labelKey: 'common.yes' },
            { value: 'false', labelKey: 'common.no' },
          ],
        })
      }
      return fields
    }
    default:
      return []
  }
}
