import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Trophy } from 'lucide-react'
import { useRating } from '@/hooks/use-rating'
import { cn } from '@/lib/utils'

const SEMESTERS = ['2026-fall', '2026-spring']

const MEDALS = ['🥇', '🥈', '🥉']

export function RatingTable() {
  const { t } = useTranslation()
  const [semester, setSemester] = useState<string>('2026-fall')
  const { data, isLoading } = useRating(semester)

  const clubs = useMemo(() => data?.clubs ?? [], [data])

  return (
    <div className="space-y-4">
      {/* Semester filter */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm text-muted-foreground">
          {t('rating.semester')}:
        </span>
        {SEMESTERS.map((sem) => (
          <button
            key={sem}
            onClick={() => setSemester(sem)}
            className={cn(
              'rounded-full px-3 py-1 text-sm transition-colors',
              semester === sem
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted text-muted-foreground hover:bg-muted/80'
            )}
          >
            {sem}
          </button>
        ))}
      </div>

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
