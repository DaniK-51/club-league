import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { SyncPanel } from '@/components/admin/sync-panel'
import { AuditList } from '@/components/admin/audit-list'
import { RulesEditor } from '@/components/admin/rules-editor'
import { cn } from '@/lib/utils'

type Tab = 'sync' | 'audit' | 'rules'

const TABS: Tab[] = ['sync', 'audit', 'rules']

export default function AdminPage() {
  const { t } = useTranslation()
  const [activeTab, setActiveTab] = useState<Tab>('sync')

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">{t('nav.admin')}</h1>

      {/* Tabs */}
      <div className="flex gap-2 border-b">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={cn(
              'px-4 py-2 text-sm font-medium transition-colors',
              activeTab === tab
                ? 'border-b-2 border-primary text-primary'
                : 'text-muted-foreground hover:text-foreground'
            )}
          >
            {t(`admin.tabs.${tab}`)}
          </button>
        ))}
      </div>

      {/* Content */}
      {activeTab === 'sync' && <SyncPanel />}
      {activeTab === 'audit' && <AuditList />}
      {activeTab === 'rules' && <RulesEditor />}
    </div>
  )
}
