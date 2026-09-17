import { useTranslation } from 'react-i18next'
import { useAuthStore } from '@/store/auth.store'

export default function RatingPage() {
  const { t } = useTranslation()
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)

  return (
    <div>
      <h1 className="text-2xl font-bold">{t('rating.title')}</h1>
      <p className="mt-2 text-muted-foreground">
        {isAuthenticated
          ? t('rating.comingSoon')
          : t('rating.publicView')}
      </p>
    </div>
  )
}
