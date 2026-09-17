import { Link, Outlet, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '@/store/auth.store'
import { useLogout } from '@/hooks/use-auth'

export function AppLayout() {
  const { t, i18n } = useTranslation()
  const user = useAuthStore((s) => s.user)
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const logout = useLogout()
  const navigate = useNavigate()

  return (
    <div className="min-h-screen">
      <header className="border-b">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <Link to="/" className="text-lg font-semibold">
            {t('app.name')}
          </Link>
          <nav className="flex items-center gap-4">
            <Link to="/rating" className="text-sm hover:underline">
              {t('nav.rating')}
            </Link>
            {isAuthenticated && user?.role === 'CLUB_LEADER' && (
              <Link to="/reports" className="text-sm hover:underline">
                {t('nav.reports')}
              </Link>
            )}
            {isAuthenticated && user?.role === 'MODERATOR' && (
              <Link to="/moderation" className="text-sm hover:underline">
                {t('nav.moderation')}
              </Link>
            )}
            <button
              onClick={() =>
                i18n.changeLanguage(i18n.language === 'ru' ? 'en' : 'ru')
              }
              className="text-sm text-muted-foreground hover:underline"
            >
              {i18n.language === 'ru' ? 'EN' : 'RU'}
            </button>
            {isAuthenticated ? (
              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground">
                  {user?.name}
                </span>
                <button
                  onClick={() => {
                    logout.mutate()
                    navigate('/login')
                  }}
                  className="text-sm text-muted-foreground hover:underline"
                >
                  {t('app.logout')}
                </button>
              </div>
            ) : (
              <Link
                to="/login"
                className="rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground"
              >
                {t('app.login')}
              </Link>
            )}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8">
        <Outlet />
      </main>
    </div>
  )
}
