import { useTranslation } from 'react-i18next'

export default function ModerationPage() {
  const { t } = useTranslation()

  return (
    <div>
      <h1 className="text-2xl font-bold">{t('nav.moderation')}</h1>
      <p className="mt-4 text-sm text-muted-foreground">
        {t('moderation.comingSoon')}
      </p>
    </div>
  )
}
