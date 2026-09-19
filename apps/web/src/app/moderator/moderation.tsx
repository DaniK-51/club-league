import { useTranslation } from 'react-i18next'
import { ModerationQueue } from '@/components/moderation/moderation-queue'

export default function ModerationPage() {
  const { t } = useTranslation()

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">{t('nav.moderation')}</h1>
      <ModerationQueue />
    </div>
  )
}
