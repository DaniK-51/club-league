import { useTranslation } from 'react-i18next'
import type { CriteriaRuleOut } from '@/lib/types'

interface RuleConfigDisplayProps {
  rule: CriteriaRuleOut
}

export function RuleConfigDisplay({ rule }: RuleConfigDisplayProps) {
  const { t } = useTranslation()
  const config = rule.config as Record<string, unknown>

  return (
    <div className="space-y-3">
      <div className="text-xs text-muted-foreground">
        {t('report.ruleType')}: <span className="font-mono">{rule.ruleType}</span>
      </div>

      <RuleConfigBody ruleType={rule.ruleType} config={config} />
    </div>
  )
}

function RuleConfigBody({
  ruleType,
  config,
}: {
  ruleType: string
  config: Record<string, unknown>
}) {
  const { t } = useTranslation()

  switch (ruleType) {
    case 'tiered':
    case 'tiered_with_bonus': {
      const tiers = (config.tiers as Array<Record<string, unknown>>) ?? []
      const bonusCondition = config.bonus_condition as
        | Record<string, unknown>
        | undefined
      return (
        <div className="space-y-2">
          <ConfigRow label={t('report.config.tiers')}>
            <table className="w-full text-xs">
              <thead>
                <tr className="text-muted-foreground">
                  <th className="text-left font-normal">{t('report.config.range')}</th>
                  <th className="text-right font-normal">{t('report.config.points')}</th>
                  {ruleType === 'tiered_with_bonus' && (
                    <th className="text-right font-normal">{t('report.config.bonus')}</th>
                  )}
                </tr>
              </thead>
              <tbody>
                {tiers.map((tier, i) => (
                  <tr key={i}>
                    <td>
                      {formatTierRange(tier)}
                    </td>
                    <td className="text-right font-medium">
                      {String(tier.pts)}
                    </td>
                    {ruleType === 'tiered_with_bonus' && (
                      <td className="text-right text-muted-foreground">
                        {tier.bonus_pts ? `+${String(tier.bonus_pts)}` : '—'}
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </ConfigRow>
          {bonusCondition && (
            <ConfigRow label={t('report.config.bonusCondition')}>
              <span className="text-xs">
                {String(bonusCondition.field)} {String(bonusCondition.operator)}{' '}
                {String(bonusCondition.value)}% → +{t('report.config.bonus')}
              </span>
            </ConfigRow>
          )}
        </div>
      )
    }

    case 'scale':
    case 'scale_with_frequency_limit':
    case 'scale_with_league_bonus': {
      const levels = (config.levels as Record<string, number>) ?? {}
      const leagueBonus = config.league_bonus as Record<string, number> | undefined
      return (
        <div className="space-y-2">
          <ConfigRow label={t('report.config.levels')}>
            <table className="w-full text-xs">
              <tbody>
                {Object.entries(levels).map(([key, pts]) => (
                  <tr key={key}>
                    <td>{t(`report.levels.${key}`, key)}</td>
                    <td className="text-right font-medium">{pts}</td>
                    {leagueBonus && (
                      <td className="text-right text-muted-foreground">
                        {leagueBonus[key] ? `+${leagueBonus[key]}` : ''}
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </ConfigRow>
          {config.max_per_month != null && (
            <ConfigRow label={t('report.config.maxPerMonth')}>
              <span className="text-xs">{String(config.max_per_month)}</span>
            </ConfigRow>
          )}
        </div>
      )
    }

    case 'binary':
    case 'binary_with_monthly_cap':
    case 'binary_scale': {
      const options =
        (config.options as Record<string, number>) ??
        Object.fromEntries(
          Object.entries(config).filter(
            ([k, v]) => typeof v === 'number' && k !== 'monthly_cap'
          )
        )
      return (
        <div className="space-y-2">
          <ConfigRow label={t('report.config.options')}>
            <table className="w-full text-xs">
              <tbody>
                {Object.entries(options).map(([key, pts]) => (
                  <tr key={key}>
                    <td>{t(`report.variants.${key}`, key)}</td>
                    <td className="text-right font-medium">{pts}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </ConfigRow>
          {config.monthly_cap != null && (
            <ConfigRow label={t('report.config.monthlyCap')}>
              <span className="text-xs">{String(config.monthly_cap)}</span>
            </ConfigRow>
          )}
        </div>
      )
    }

    case 'per_unit_with_bonus':
      return (
        <div className="space-y-2">
          <ConfigRow label={t('report.config.basePerPartner')}>
            <span className="text-xs font-medium">
              {String(config.base_per_partner)}
            </span>
          </ConfigRow>
          {config.cross_type_bonus != null && (
            <ConfigRow label={t('report.config.crossTypeBonus')}>
              <span className="text-xs font-medium">
                +{String(config.cross_type_bonus)}
              </span>
            </ConfigRow>
          )}
        </div>
      )

    case 'fixed_monthly_with_per_unit':
      return (
        <div className="space-y-2">
          <ConfigRow label={t('report.config.baseMonthly')}>
            <span className="text-xs font-medium">
              {String(config.base_monthly)}
            </span>
          </ConfigRow>
          <ConfigRow label={t('report.config.perExtra')}>
            <span className="text-xs font-medium">
              +{String(config.per_extra_social)}
            </span>
          </ConfigRow>
        </div>
      )

    case 'discretionary':
      return (
        <ConfigRow label={t('report.config.range')}>
          <span className="text-xs font-medium">
            {String(config.min)} — {String(config.max)}
          </span>
        </ConfigRow>
      )

    case 'fixed_per_event_with_monthly_cap':
      return (
        <div className="space-y-2">
          <ConfigRow label={t('report.config.perEvent')}>
            <span className="text-xs font-medium">
              {String(config.per_event)}
            </span>
          </ConfigRow>
          <ConfigRow label={t('report.config.monthlyCap')}>
            <span className="text-xs">{String(config.monthly_cap)}</span>
          </ConfigRow>
        </div>
      )

    case 'per_person_per_month': {
      const perTrainer = config.per_trainer_per_month
      const perLeader = config.per_leader_per_month
      return (
        <div className="space-y-2">
          <ConfigRow
            label={
              perTrainer != null
                ? t('report.config.perTrainer')
                : t('report.config.perLeader')
            }
          >
            <span className="text-xs font-medium">
              {String(perTrainer ?? perLeader)}
            </span>
          </ConfigRow>
          <ConfigRow
            label={
              perTrainer != null
                ? t('report.config.maxTrainers')
                : t('report.config.maxLeaders')
            }
          >
            <span className="text-xs">
              {String(config.max_trainers ?? config.max_leaders)}
            </span>
          </ConfigRow>
        </div>
      )
    }

    case 'scale_split_mode':
    case 'scale_with_conditional_modifier': {
      const individual = config.individual as Record<string, number> | undefined
      const team = config.team as Record<string, number> | undefined
      return (
        <div className="space-y-3">
          {individual && (
            <ConfigRow label={t('report.modes.individual')}>
              <table className="w-full text-xs">
                <tbody>
                  {Object.entries(individual).map(([key, pts]) => (
                    <tr key={key}>
                      <td>{t(`report.levels.${key}`, key)}</td>
                      <td className="text-right font-medium">{pts}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </ConfigRow>
          )}
          {team && (
            <ConfigRow label={t('report.modes.team')}>
              <table className="w-full text-xs">
                <tbody>
                  {Object.entries(team).map(([key, pts]) => (
                    <tr key={key}>
                      <td>{t(`report.levels.${key}`, key)}</td>
                      <td className="text-right font-medium">{pts}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </ConfigRow>
          )}
        </div>
      )
    }

    case 'scale_with_conditional_bonus': {
      const levels = (config.levels as Record<string, number>) ?? {}
      const focusBonus = config.full_club_focus_bonus as
        | Record<string, number>
        | undefined
      return (
        <ConfigRow label={t('report.config.levels')}>
          <table className="w-full text-xs">
            <thead>
              <tr className="text-muted-foreground">
                <th className="text-left font-normal">{t('report.config.level')}</th>
                <th className="text-right font-normal">{t('report.config.points')}</th>
                <th className="text-right font-normal">
                  {t('report.config.focusBonus')}
                </th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(levels).map(([key, pts]) => (
                <tr key={key}>
                  <td>{t(`report.levels.${key}`, key)}</td>
                  <td className="text-right font-medium">{pts}</td>
                  <td className="text-right text-muted-foreground">
                    {focusBonus?.[key] ? `+${focusBonus[key]}` : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </ConfigRow>
      )
    }

    default:
      return (
        <pre className="text-xs text-muted-foreground">
          {JSON.stringify(config, null, 2)}
        </pre>
      )
  }
}

function ConfigRow({
  label,
  children,
}: {
  label: string
  children: React.ReactNode
}) {
  return (
    <div>
      <div className="mb-1 text-xs font-medium text-muted-foreground">
        {label}
      </div>
      {children}
    </div>
  )
}

function formatTierRange(tier: Record<string, unknown>): string {
  if (tier.count != null) {
    return `${tier.count}`
  }
  const min = tier.min as number | null
  const max = tier.max as number | null
  if (min != null && max == null) {
    return `${min}+`
  }
  if (min != null && max != null) {
    return `${min}–${max}`
  }
  return '—'
}
