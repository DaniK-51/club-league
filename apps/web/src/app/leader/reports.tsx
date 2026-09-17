import { useTranslation } from 'react-i18next'
import { useAuthStore } from '@/store/auth.store'
import { useMe } from '@/hooks/use-auth'

export default function ReportsPage() {
  const { t } = useTranslation()
  const user = useAuthStore((s) => s.user)
  const { data: me } = useMe()

  return (
    <div>
      <h1 className="text-2xl font-bold">{t('nav.reports')}</h1>
      <p className="mt-2 text-muted-foreground">
        {t('reports.welcome', { name: me?.name ?? user?.name ?? '' })}
      </p>
      <p className="mt-4 text-sm text-muted-foreground">
        {t('reports.comingSoon')}
      </p>
    </div>
  )
}
