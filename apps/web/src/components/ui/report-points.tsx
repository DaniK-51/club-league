import { useTranslation } from 'react-i18next'

interface ReportPointsProps {
  calculated: number | null
  final: number | null
  showLabels?: boolean
}

export function ReportPoints({ calculated, final, showLabels = false }: ReportPointsProps) {
  const { t } = useTranslation()

  if (calculated == null && final == null) return null

  return (
    <div className="text-right">
      {calculated != null && (
        <p className="text-sm text-muted-foreground">
          {showLabels && <>{t('moderation.calculated')}: </>}
          <span className="font-medium">{calculated}</span>
          {!showLabels && <> {t('report.pointsUnit')}</>}
        </p>
      )}
      {final != null && (
        <p className="text-sm font-semibold">
          {showLabels && <>{t('moderation.final')}: </>}
          <span className="text-primary">{final}</span>
          {!showLabels && <> {t('report.pointsUnit')}</>}
        </p>
      )}
    </div>
  )
}
