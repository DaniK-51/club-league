import { useTranslation } from 'react-i18next'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import type { CriteriaRuleOut } from '@/lib/types'

interface DynamicFieldsProps {
  rule: CriteriaRuleOut
  values: Record<string, unknown>
  onChange: (values: Record<string, unknown>) => void
}

/**
 * Renders form fields based on rule type config.
 * Field names come from rule config (e.g. level_field, count_field).
 */
export function DynamicRuleFields({ rule, values, onChange }: DynamicFieldsProps) {
  const { t } = useTranslation()
  const config = rule.config as Record<string, unknown>

  const setField = (key: string, value: unknown) => {
    onChange({ ...values, [key]: value })
  }

  switch (rule.ruleType) {
    case 'tiered':
    case 'tiered_with_bonus': {
      const countField = (config.count_field as string) ?? 'count'
      return (
        <NumberField
          label={t('report.fields.count')}
          value={values[countField] as number ?? ''}
          onChange={(v) => setField(countField, v)}
          min={0}
        />
      )
    }

    case 'scale':
    case 'scale_with_frequency_limit':
    case 'scale_with_league_bonus': {
      const levelField = (config.level_field as string) ?? 'level'
      const levels = (config.levels as Record<string, number>) ?? {}
      return (
        <SelectField
          label={t('report.fields.level')}
          value={(values[levelField] as string) ?? ''}
          options={Object.keys(levels).map((k) => ({
            value: k,
            label: t(`report.levels.${k}`, k),
          }))}
          onChange={(v) => setField(levelField, v)}
        />
      )
    }

    case 'binary':
    case 'binary_with_monthly_cap':
    case 'binary_scale': {
      const variantField = (config.variant_field as string) ?? 'variant'
      // config may be flat ({passive: 100, active: 350}) or {options: {...}}
      const options =
        (config.options as Record<string, number>) ??
        Object.fromEntries(
          Object.entries(config).filter(
            ([k, v]) =>
              typeof v === 'number' &&
              !['monthly_cap'].includes(k)
          )
        )
      return (
        <SelectField
          label={t('report.fields.variant')}
          value={(values[variantField] as string) ?? ''}
          options={Object.keys(options).map((k) => ({
            value: k,
            label: t(`report.variants.${k}`, k),
          }))}
          onChange={(v) => setField(variantField, v)}
        />
      )
    }

    case 'per_unit_with_bonus': {
      const partnersField = (config.partners_field as string) ?? 'partners'
      const crossTypeField = (config.cross_type_field as string) ?? 'cross_type'
      return (
        <div className="space-y-4">
          <NumberField
            label={t('report.fields.partners')}
            value={values[partnersField] as number ?? ''}
            onChange={(v) => setField(partnersField, v)}
            min={1}
          />
          <CheckboxField
            label={t('report.fields.crossType')}
            value={(values[crossTypeField] as boolean) ?? false}
            onChange={(v) => setField(crossTypeField, v)}
          />
        </div>
      )
    }

    case 'fixed_monthly_with_per_unit': {
      const extraField = (config.extra_field as string) ?? 'extra_socials'
      return (
        <NumberField
          label={t('report.fields.extraSocials')}
          value={values[extraField] as number ?? ''}
          onChange={(v) => setField(extraField, v)}
          min={0}
        />
      )
    }

    case 'scale_with_conditional_bonus': {
      const levelField = (config.level_field as string) ?? 'level'
      const focusField = (config.focus_field as string) ?? 'full_club_focus'
      const levels = (config.levels as Record<string, number>) ?? {}
      return (
        <div className="space-y-4">
          <SelectField
            label={t('report.fields.level')}
            value={(values[levelField] as string) ?? ''}
            options={Object.keys(levels).map((k) => ({
              value: k,
              label: t(`report.levels.${k}`, k),
            }))}
            onChange={(v) => setField(levelField, v)}
          />
          <CheckboxField
            label={t('report.fields.fullClubFocus')}
            value={(values[focusField] as boolean) ?? false}
            onChange={(v) => setField(focusField, v)}
          />
        </div>
      )
    }

    case 'discretionary': {
      const pointsField = (config.points_field as string) ?? 'points'
      const min = (config.min as number) ?? 0
      const max = (config.max as number) ?? 300
      return (
        <NumberField
          label={t('report.fields.points', { min, max })}
          value={values[pointsField] as number ?? ''}
          onChange={(v) => setField(pointsField, v)}
          min={min}
          max={max}
        />
      )
    }

    case 'per_person_per_month': {
      const trainersField = (config.trainers_field as string) ?? 'trainers'
      const leadersField = (config.leaders_field as string) ?? 'leaders'
      const hasTrainers = config.per_trainer_per_month != null
      const field = hasTrainers ? trainersField : leadersField
      const label = hasTrainers
        ? t('report.fields.trainers')
        : t('report.fields.leaders')
      return (
        <NumberField
          label={label}
          value={values[field] as number ?? ''}
          onChange={(v) => setField(field, v)}
          min={1}
        />
      )
    }

    case 'scale_split_mode':
    case 'scale_with_conditional_modifier': {
      const modeField = (config.mode_field as string) ?? 'mode'
      const levelField = (config.level_field as string) ?? 'level'
      const mode = (values[modeField] as string) ?? 'individual'
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
            value={(values[levelField] as string) ?? ''}
            options={Object.keys(levels).map((k) => ({
              value: k,
              label: t(`report.levels.${k}`, k),
            }))}
            onChange={(v) => setField(levelField, v)}
          />
          {rule.ruleType === 'scale_with_conditional_modifier' && (
            <CheckboxField
              label={t('report.fields.isHost')}
              value={
                (values[(config.is_host_field as string) ?? 'is_host'] as boolean) ?? false
              }
              onChange={(v) =>
                setField((config.is_host_field as string) ?? 'is_host', v)
              }
            />
          )}
        </div>
      )
    }

    case 'fixed_per_event_with_monthly_cap':
    case 'combined_cap':
    default:
      // No extra fields needed — links + date are enough
      return (
        <p className="text-sm text-muted-foreground">
          {t('report.noExtraFields')}
        </p>
      )
  }
}

// === Primitive field components ===

function NumberField({
  label,
  value,
  onChange,
  min,
  max,
}: {
  label: string
  value: number | ''
  onChange: (v: number) => void
  min?: number
  max?: number
}) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      <Input
        type="number"
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        min={min}
        max={max}
      />
    </div>
  )
}

function SelectField({
  label,
  value,
  options,
  onChange,
}: {
  label: string
  value: string
  options: { value: string; label: string }[]
  onChange: (v: string) => void
}) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
      >
        <option value="">—</option>
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  )
}

function CheckboxField({
  label,
  value,
  onChange,
}: {
  label: string
  value: boolean
  onChange: (v: boolean) => void
}) {
  return (
    <label className="flex items-center gap-2 text-sm">
      <input
        type="checkbox"
        checked={value}
        onChange={(e) => onChange(e.target.checked)}
        className="h-4 w-4 rounded border-input"
      />
      {label}
    </label>
  )
}
