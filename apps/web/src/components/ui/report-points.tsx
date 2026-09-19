import { useTranslation } from 'react-i18next'

interface ReportPointsProps {
  calculated: number | null
  final: number | null
}

export function ReportPoints({ calculated, final }: ReportPointsProps) {
  const { t } = useTranslation()

  // Show effective points: final if set, otherwise calculated
  const value = final ?? calculated
  if (value == null) return null

  return (
    <span className="text-right text-sm">
      <span className={final != null ? 'font-semibold text-primary' : 'font-medium'}>
        {value}
      </span>
      <span className="text-muted-foreground"> {t('report.pointsUnit')}</span>
    </span>
  )
}
