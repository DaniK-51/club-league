import { useTranslation } from 'react-i18next'
import { RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useSyncStatus, useForceSync } from '@/hooks/use-admin'
import { cn } from '@/lib/utils'

export function SyncPanel() {
  const { t } = useTranslation()
  const { data: status, isLoading } = useSyncStatus()
  const forceSync = useForceSync()

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">{t('admin.sync.title')}</h2>
        <Button
          size="sm"
          onClick={() => forceSync.mutate()}
          disabled={forceSync.isPending || status?.pending}
        >
          <RefreshCw
            className={cn('h-3 w-3', forceSync.isPending && 'animate-spin')}
          />
          {t('admin.sync.force')}
        </Button>
      </div>

      {isLoading ? (
        <p className="text-muted-foreground">{t('common.loading')}</p>
      ) : status ? (
        <div className="rounded-md border p-4">
          <dl className="grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
            <div>
              <dt className="text-muted-foreground">{t('admin.sync.status')}</dt>
              <dd>
                <span
                  className={cn(
                    'inline-block rounded-full px-2 py-0.5 text-xs font-medium',
                    status.pending
                      ? 'bg-yellow-100 text-yellow-800'
                      : 'bg-green-100 text-green-800'
                  )}
                >
                  {status.pending
                    ? t('admin.sync.pending')
                    : t('admin.sync.idle')}
                </span>
              </dd>
            </div>
            <div>
              <dt className="text-muted-foreground">{t('admin.sync.lastRun')}</dt>
              <dd>
                {status.lastRunAt
                  ? new Date(status.lastRunAt).toLocaleString('ru-RU')
                  : '—'}
              </dd>
            </div>
            <div>
              <dt className="text-muted-foreground">{t('admin.sync.runCount')}</dt>
              <dd>{status.runCount}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">{t('admin.sync.debounce')}</dt>
              <dd>{status.debounceSeconds}s</dd>
            </div>
          </dl>
          {status.lastError && (
            <p className="mt-3 text-sm text-destructive">
              {t('admin.sync.lastError')}: {status.lastError}
            </p>
          )}
        </div>
      ) : null}
    </div>
  )
}
