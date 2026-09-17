import { useEffect, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useSsoCallback } from '@/hooks/use-auth'
import { useAuthStore } from '@/store/auth.store'

export default function AuthCallbackPage() {
  const { t } = useTranslation()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const mutation = useSsoCallback()
  const user = useAuthStore((s) => s.user)
  const started = useRef(false)

  const code = searchParams.get('code')
  const error = searchParams.get('error')

  useEffect(() => {
    if (started.current) return
    started.current = true

    if (error) {
      navigate('/login', { replace: true })
      return
    }
    if (!code) {
      navigate('/login', { replace: true })
      return
    }
    mutation.mutate(code)
  }, [code, error, mutation, navigate])

  useEffect(() => {
    if (!user) return
    if (user.role === 'MODERATOR') {
      navigate('/moderation', { replace: true })
    } else if (user.role === 'CLUB_LEADER') {
      navigate('/reports', { replace: true })
    } else {
      navigate('/rating', { replace: true })
    }
  }, [user, navigate])

  if (mutation.isError) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <p className="text-destructive">{t('auth.loginFailed')}</p>
          <button
            onClick={() => navigate('/login')}
            className="mt-4 rounded-md bg-primary px-4 py-2 text-primary-foreground"
          >
            {t('auth.tryAgain')}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen items-center justify-center">
      <p className="text-muted-foreground">{t('auth.loggingIn')}</p>
    </div>
  )
}
