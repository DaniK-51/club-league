import { useTranslation } from 'react-i18next'
import { NumberField, SelectField, CheckboxField } from '@/components/ui/form-fields'
import type { CriteriaRuleOut } from '@/lib/types'

interface DynamicFieldsProps {
  rule: CriteriaRuleOut
  values: Record<string, unknown>
  onChange: (values: Record<string, unknown>) => void
}

function getField(config: Record<string, unknown>, key: string, fallback: string): string {
  return (config[key] as string) ?? fallback
}

function levelOptions(levels: Record<string, number>, t: (key: string, fallback: string) => string) {
  return Object.keys(levels).map((k) => ({
    value: k,
    label: t(`report.levels.${k}`, k),
  }))
}

export function DynamicRuleFields({ rule, values, onChange }: DynamicFieldsProps) {
  const { t } = useTranslation()
  const config = rule.config as Record<string, unknown>

  const setField = (key: string, value: unknown) => {
    onChange({ ...values, [key]: value })
  }

  const num = (key: string) => (values[key] as number) ?? ''
  const str = (key: string) => (values[key] as string) ?? ''
  const bool = (key: string) => (values[key] as boolean) ?? false

  switch (rule.ruleType) {
    case 'tiered':
    case 'tiered_with_bonus': {
      const field = getField(config, 'count_field', 'count')
      return (
        <NumberField
          label={t('report.fields.count')}
          value={num(field)}
          onChange={(v) => setField(field, v)}
          min={0}
        />
      )
    }

    case 'scale':
    case 'scale_with_frequency_limit':
    case 'scale_with_league_bonus': {
      const field = getField(config, 'level_field', 'level')
      const levels = (config.levels as Record<string, number>) ?? {}
      return (
        <SelectField
          label={t('report.fields.level')}
          value={str(field)}
          options={levelOptions(levels, t)}
          onChange={(v) => setField(field, v)}
        />
      )
    }

    case 'binary':
    case 'binary_with_monthly_cap':
    case 'binary_scale': {
      const field = getField(config, 'variant_field', 'variant')
      const options =
        (config.options as Record<string, number>) ??
        Object.fromEntries(
          Object.entries(config).filter(
            ([k, v]) => typeof v === 'number' && k !== 'monthly_cap'
          )
        )
      return (
        <SelectField
          label={t('report.fields.variant')}
          value={str(field)}
          options={Object.keys(options).map((k) => ({
            value: k,
            label: t(`report.variants.${k}`, k),
          }))}
          onChange={(v) => setField(field, v)}
        />
      )
    }

    case 'per_unit_with_bonus': {
      const partnersField = getField(config, 'partners_field', 'partners')
      const crossTypeField = getField(config, 'cross_type_field', 'cross_type')
      return (
        <div className="space-y-4">
          <NumberField
            label={t('report.fields.partners')}
            value={num(partnersField)}
            onChange={(v) => setField(partnersField, v)}
            min={1}
          />
          <CheckboxField
            label={t('report.fields.crossType')}
            value={bool(crossTypeField)}
            onChange={(v) => setField(crossTypeField, v)}
          />
        </div>
      )
    }

    case 'fixed_monthly_with_per_unit': {
      const field = getField(config, 'extra_field', 'extra_socials')
      return (
        <NumberField
          label={t('report.fields.extraSocials')}
          value={num(field)}
          onChange={(v) => setField(field, v)}
          min={0}
        />
      )
    }

    case 'scale_with_conditional_bonus': {
      const levelField = getField(config, 'level_field', 'level')
      const focusField = getField(config, 'focus_field', 'full_club_focus')
      const levels = (config.levels as Record<string, number>) ?? {}
      return (
        <div className="space-y-4">
          <SelectField
            label={t('report.fields.level')}
            value={str(levelField)}
            options={levelOptions(levels, t)}
            onChange={(v) => setField(levelField, v)}
          />
          <CheckboxField
            label={t('report.fields.fullClubFocus')}
            value={bool(focusField)}
            onChange={(v) => setField(focusField, v)}
          />
        </div>
      )
    }

    case 'discretionary': {
      const field = getField(config, 'points_field', 'points')
      const min = (config.min as number) ?? 0
      const max = (config.max as number) ?? 300
      return (
        <NumberField
          label={t('report.fields.points', { min, max })}
          value={num(field)}
          onChange={(v) => setField(field, v)}
          min={min}
          max={max}
        />
      )
    }

    case 'per_person_per_month': {
      const hasTrainers = config.per_trainer_per_month != null
      const field = hasTrainers
        ? getField(config, 'trainers_field', 'trainers')
        : getField(config, 'leaders_field', 'leaders')
      return (
        <NumberField
          label={hasTrainers ? t('report.fields.trainers') : t('report.fields.leaders')}
          value={num(field)}
          onChange={(v) => setField(field, v)}
          min={1}
        />
      )
    }

    case 'scale_split_mode':
    case 'scale_with_conditional_modifier': {
      const modeField = getField(config, 'mode_field', 'mode')
      const levelField = getField(config, 'level_field', 'level')
      const isHostField = getField(config, 'is_host_field', 'is_host')
      const mode = str(modeField) || 'individual'
      const levels =
        (config[mode] as Record<string, number>) ??
        (config.individual as Record<string, number>) ??
        {}
      return (
        <div className="space-y-4">
          <SelectField
            label={t('report.fields.mode')}
            value={mode}
            options={[
              { value: 'individual', label: t('report.modes.individual') },
              { value: 'team', label: t('report.modes.team') },
            ]}
            onChange={(v) => {
              setField(modeField, v)
              setField(levelField, '')
            }}
          />
          <SelectField
            label={t('report.fields.level')}
            value={str(levelField)}
            options={levelOptions(levels, t)}
            onChange={(v) => setField(levelField, v)}
          />
          {rule.ruleType === 'scale_with_conditional_modifier' && (
            <CheckboxField
              label={t('report.fields.isHost')}
              value={bool(isHostField)}
              onChange={(v) => setField(isHostField, v)}
            />
          )}
        </div>
      )
    }

    default:
      return (
        <p className="text-sm text-muted-foreground">
          {t('report.noExtraFields')}
        </p>
      )
  }
}
