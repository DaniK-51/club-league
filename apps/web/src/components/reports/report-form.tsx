import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { AlertTriangle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Dialog } from '@/components/ui/dialog'
import { SelectField } from '@/components/ui/form-fields'
import { LinkInput } from './link-input'
import { DynamicRuleFields } from './dynamic-rule-fields'
import { useCriteria, useCreateReport } from '@/hooks/use-reports'
import { isOverdue, toIsoString, toDateInputValue } from '@/lib/date-utils'
import { ApiError } from '@/lib/types'
import type { CreateReportDTO } from '@/lib/types'

export function ReportForm() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const { data: criteriaList, isLoading: criteriaLoading } = useCriteria()
  const createReport = useCreateReport()

  const [criteriaId, setCriteriaId] = useState('')
  const [activityDate, setActivityDate] = useState(toDateInputValue())
  const [links, setLinks] = useState<string[]>([])
  const [reportData, setReportData] = useState<Record<string, unknown>>({})
  const [showOverdueModal, setShowOverdueModal] = useState(false)
  const [apiError, setApiError] = useState<string | null>(null)

  const selectedCriteria = useMemo(
    () => criteriaList?.find((c) => c.id === criteriaId),
    [criteriaList, criteriaId]
  )

  const activeRule = useMemo(
    () => selectedCriteria?.rules?.[0],
    [selectedCriteria]
  )

  const overdue = activityDate ? isOverdue(toIsoString(activityDate)) : false

  const isValid = criteriaId && activityDate && links.length > 0

  const doSubmit = () => {
    setApiError(null)
    const dto: CreateReportDTO = {
      criteriaId,
      activityDate: toIsoString(activityDate),
      reportData,
      links,
    }
    createReport.mutate(dto, {
      onSuccess: () => navigate('/reports'),
      onError: (err) => {
        if (err instanceof ApiError) {
          setApiError(err.message)
        } else {
          setApiError(t('report.submitError'))
        }
      },
    })
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!isValid) return

    if (overdue) {
      setShowOverdueModal(true)
      return
    }
    doSubmit()
  }

  if (criteriaLoading) {
    return <p className="text-muted-foreground">{t('common.loading')}</p>
  }

  return (
    <>
      <form onSubmit={handleSubmit} className="max-w-2xl space-y-6">
        {/* Criteria select */}
        <SelectField
          label={t('report.criteria')}
          value={criteriaId}
          options={(criteriaList ?? []).map((c) => ({
            value: c.id,
            label: `${c.code} — ${i18n.language === 'ru' ? c.nameRu : c.nameEn}`,
          }))}
          onChange={(v) => {
            setCriteriaId(v)
            setReportData({})
          }}
          id="criteria"
        />

        {/* Activity date */}
        <div className="space-y-1.5">
          <Label htmlFor="activityDate">{t('report.activityDate')}</Label>
          <Input
            id="activityDate"
            type="date"
            value={activityDate}
            onChange={(e) => setActivityDate(e.target.value)}
            max={toDateInputValue()}
            required
          />
          {overdue && (
            <p className="flex items-center gap-1 text-sm text-yellow-600">
              <AlertTriangle className="h-3 w-3" />
              {t('report.overdueWarning')}
            </p>
          )}
        </div>

        {/* Dynamic fields from rule config */}
        {activeRule && (
          <div className="rounded-md border bg-muted/30 p-4">
            <p className="mb-3 text-sm font-medium">
              {t('report.additionalData')}
            </p>
            <DynamicRuleFields
              rule={activeRule}
              values={reportData}
              onChange={setReportData}
            />
          </div>
        )}

        {/* Links */}
        <div className="space-y-1.5">
          <Label>{t('report.links')}</Label>
          <p className="text-xs text-muted-foreground">
            {t('report.linksHint')}
          </p>
          <LinkInput links={links} onChange={setLinks} />
        </div>

        {/* API error */}
        {apiError && (
          <p className="text-sm text-destructive">{apiError}</p>
        )}

        {/* Actions */}
        <div className="flex gap-3">
          <Button type="submit" disabled={!isValid || createReport.isPending}>
            {createReport.isPending
              ? t('common.submitting')
              : t('report.saveDraft')}
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={() => navigate('/reports')}
          >
            {t('common.cancel')}
          </Button>
        </div>
      </form>

      {/* Overdue confirmation modal */}
      <Dialog
        open={showOverdueModal}
        onClose={() => setShowOverdueModal(false)}
        title={t('report.overdueTitle')}
      >
        <p className="text-sm text-muted-foreground">
          {t('report.overdueConfirm')}
        </p>
        <div className="mt-4 flex gap-3">
          <Button
            onClick={() => {
              setShowOverdueModal(false)
              doSubmit()
            }}
          >
            {t('report.overdueProceed')}
          </Button>
          <Button
            variant="outline"
            onClick={() => setShowOverdueModal(false)}
          >
            {t('common.cancel')}
          </Button>
        </div>
      </Dialog>
    </>
  )
}
