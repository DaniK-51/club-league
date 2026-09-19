import { useTranslation } from 'react-i18next'
import { redirectToSso } from '@/lib/sso'

export default function LoginPage() {
  const { t } = useTranslation()

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="w-full max-w-sm space-y-6 text-center">
        <h1 className="text-3xl font-bold">{t('app.name')}</h1>
        <p className="text-muted-foreground">
          {t('auth.loginSubtitle')}
        </p>
        <button
          onClick={redirectToSso}
          className="w-full rounded-md bg-primary px-4 py-3 font-medium text-primary-foreground hover:bg-primary/90"
        >
          {t('app.login')}
        </button>
      </div>
    </div>
  )
}
