import { useTranslation } from 'react-i18next'
import { RatingTable } from '@/components/rating/rating-table'

export default function RatingPage() {
  const { t } = useTranslation()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">{t('rating.title')}</h1>
        <p className="text-sm text-muted-foreground">
          {t('rating.subtitle')}
        </p>
      </div>
      <RatingTable />
    </div>
  )
}
