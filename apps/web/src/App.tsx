import { Routes, Route } from 'react-router-dom'
import { useTranslation } from 'react-i18next'

function HomePage() {
  const { t, i18n } = useTranslation()

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-bold">{t('app.name')}</h1>
        <p className="mt-2 text-muted-foreground">Frontend scaffold ready</p>
        <button
          onClick={() => i18n.changeLanguage(i18n.language === 'ru' ? 'en' : 'ru')}
          className="mt-4 rounded-md bg-primary px-4 py-2 text-primary-foreground"
        >
          {i18n.language === 'ru' ? 'EN' : 'RU'}
        </button>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
    </Routes>
  )
}
