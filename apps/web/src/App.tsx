import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuthStore } from '@/store/auth.store'
import { AppLayout } from '@/components/layout/app-layout'
import LoginPage from '@/app/auth/login'
import AuthCallbackPage from '@/app/auth/callback'
import RatingPage from '@/app/public/rating'
import ReportsPage from '@/app/leader/reports'
import ModerationPage from '@/app/moderator/moderation'
import AdminPage from '@/app/admin/admin'

function RequireAuth({
  children,
  roles,
}: {
  children: React.ReactNode
  roles?: string[]
}) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const user = useAuthStore((s) => s.user)

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }
  if (roles && user && !roles.includes(user.role)) {
    return <Navigate to="/rating" replace />
  }
  return <>{children}</>
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/auth/callback" element={<AuthCallbackPage />} />

      <Route element={<AppLayout />}>
        <Route path="/" element={<Navigate to="/rating" replace />} />
        <Route path="/rating" element={<RatingPage />} />

        <Route
          path="/reports/*"
          element={
            <RequireAuth roles={['CLUB_LEADER', 'MODERATOR']}>
              <ReportsPage />
            </RequireAuth>
          }
        />

        <Route
          path="/moderation"
          element={
            <RequireAuth roles={['MODERATOR']}>
              <ModerationPage />
            </RequireAuth>
          }
        />

        <Route
          path="/admin"
          element={
            <RequireAuth roles={['MODERATOR']}>
              <AdminPage />
            </RequireAuth>
          }
        />
      </Route>

      <Route path="*" element={<Navigate to="/rating" replace />} />
    </Routes>
  )
}
