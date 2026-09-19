import { Route, Routes } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ReportList } from '@/components/reports/report-list'
import { ReportForm } from '@/components/reports/report-form'
import { ReportDetail } from '@/components/reports/report-detail'

function ReportsIndex() {
  const { t } = useTranslation()

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">{t('nav.reports')}</h1>
      <ReportList />
    </div>
  )
}

function NewReport() {
  const { t } = useTranslation()

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">{t('report.create')}</h1>
      <ReportForm />
    </div>
  )
}

function ReportDetailPage() {
  return (
    <div className="space-y-6">
      <ReportDetail />
    </div>
  )
}

export default function ReportsPage() {
  return (
    <Routes>
      <Route index element={<ReportsIndex />} />
      <Route path="new" element={<NewReport />} />
      <Route path=":id" element={<ReportDetailPage />} />
    </Routes>
  )
}
