import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Trophy } from 'lucide-react'
import { useRating } from '@/hooks/use-rating'
import { usePublicPeriods } from '@/hooks/use-public-periods'
import { usePeriods } from '@/hooks/use-periods'
import { useAuthStore } from '@/store/auth.store'
import type { PeriodOut } from '@/lib/types'
import { cn } from '@/lib/utils'

const MEDALS = ['🥇', '🥈', '🥉']

/** Until GET /api/periods ships, moderator can use admin list; guests get fallback names. */
const FALLBACK_PERIODS: PeriodOut[] = [
  {
    id: 'fb-fall',
    name: '2026-fall',
    startDate: '2026-09-01',
    endDate: '2026-12-31',
    isArchived: false,
    reportCount: 0,
  },
  {
    id: 'fb-spring',
    name: '2026-spring',
    startDate: '2026-01-01',
    endDate: '2026-05-31',
    isArchived: false,
    reportCount: 0,
  },
  {
    id: 'fb-summer',
    name: '2026-summer',
    startDate: '2026-06-01',
    endDate: '2026-08-31',
    isArchived: false,
    reportCount: 0,
  },
]

export function RatingTable() {
  const { t } = useTranslation()
  const role = useAuthStore((s) => s.user?.role)
  const isModerator = role === 'MODERATOR'

  const publicPeriods = usePublicPeriods()
  const adminPeriods = usePeriods(isModerator)

  const [period, setPeriod] = useState<string>('')

  const periodOptions = useMemo<PeriodOut[]>(() => {
    if (publicPeriods.data?.length) return publicPeriods.data
    if (isModerator && adminPeriods.data?.length) return adminPeriods.data
    return FALLBACK_PERIODS
  }, [publicPeriods.data, adminPeriods.data, isModerator])

  const { data, isLoading } = useRating(period ? { period } : undefined)
  const clubs = useMemo(() => data?.clubs ?? [], [data])

  return (
    <div className="space-y-4">
      {/* Period filter — all roles, including archived */}
      {periodOptions.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm text-muted-foreground">
            {t('rating.period')}:
          </span>
          <button
            onClick={() => setPeriod('')}
            className={cn(
              'rounded-full px-3 py-1 text-sm transition-colors',
              period === ''
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted text-muted-foreground hover:bg-muted/80'
            )}
          >
            {t('rating.currentPeriod')}
          </button>
          {periodOptions.map((p) => (
            <button
              key={p.id}
              onClick={() => setPeriod(p.name)}
              className={cn(
                'rounded-full px-3 py-1 text-sm transition-colors',
                period === p.name
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted text-muted-foreground hover:bg-muted/80',
                period !== p.name &&
                  p.isArchived &&
                  'opacity-70 ring-1 ring-muted-foreground/30'
              )}
              title={
                p.isArchived ? t('rating.archivedPeriod') : undefined
              }
            >
              {p.name}
              {p.isArchived && (
                <span className="ml-1 text-[10px] uppercase opacity-80">
                  {t('rating.archivedShort')}
                </span>
              )}
            </button>
          ))}
        </div>
      )}

      {/* Loading / Empty */}
      {isLoading ? (
        <p className="text-muted-foreground">{t('common.loading')}</p>
      ) : clubs.length === 0 ? (
        <div className="rounded-md border border-dashed p-8 text-center">
          <p className="text-muted-foreground">{t('rating.empty')}</p>
        </div>
      ) : (
        /* Table */
        <div className="overflow-x-auto rounded-md border">
          <table className="w-full">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="w-16 px-4 py-3 text-left text-sm font-medium text-muted-foreground">
                  #
                </th>
                <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">
                  {t('rating.club')}
                </th>
                <th className="px-4 py-3 text-right text-sm font-medium text-muted-foreground">
                  {t('rating.points')}
                </th>
                <th className="hidden px-4 py-3 text-left text-sm font-medium text-muted-foreground md:table-cell">
                  {t('rating.breakdown')}
                </th>
              </tr>
            </thead>
            <tbody>
              {clubs.map((club, index) => (
                <tr
                  key={club.id}
                  className={cn(
                    'border-b last:border-0',
                    index < 3 && 'bg-muted/20'
                  )}
                >
                  <td className="px-4 py-3 text-sm">
                    {index < 3 ? (
                      <span className="text-lg">{MEDALS[index]}</span>
                    ) : (
                      <span className="text-muted-foreground">{index + 1}</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      {index === 0 && (
                        <Trophy className="h-4 w-4 text-yellow-500" />
                      )}
                      <span className="font-medium">{club.name}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span className="text-lg font-semibold">
                      {club.totalPoints}
                    </span>
                  </td>
                  <td className="hidden px-4 py-3 md:table-cell">
                    {Object.keys(club.breakdown).length > 0 ? (
                      <div className="flex flex-wrap gap-1">
                        {Object.entries(club.breakdown).map(([code, pts]) => (
                          <span
                            key={code}
                            className="rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground"
                          >
                            {code}: {pts}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="text-xs text-muted-foreground">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
