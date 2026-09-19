import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Save } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { useCriteria } from '@/hooks/use-reports'
import { useRule, useUpdateRule } from '@/hooks/use-admin'
import { ApiError, type RuleOut } from '@/lib/types'

export function RulesEditor() {
  const { t, i18n } = useTranslation()
  const { data: criteriaList } = useCriteria()
  const [selectedRuleId, setSelectedRuleId] = useState('')

  const { data: rule } = useRule(selectedRuleId, !!selectedRuleId)

  const allRules = (criteriaList ?? []).flatMap((c) =>
    (c.rules ?? []).map((r) => ({
      ...r,
      criteriaCode: c.code,
      criteriaName: i18n.language === 'ru' ? c.nameRu : c.nameEn,
    }))
  )

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">{t('admin.rules.title')}</h2>

      <div className="space-y-1.5">
        <Label htmlFor="ruleSelect">{t('admin.rules.selectRule')}</Label>
        <select
          id="ruleSelect"
          value={selectedRuleId}
          onChange={(e) => setSelectedRuleId(e.target.value)}
          className="flex h-9 w-full max-w-md rounded-md border border-input bg-transparent px-3 py-1 text-sm"
        >
          <option value="">—</option>
          {allRules.map((r) => (
            <option key={r.id} value={r.id}>
              {r.criteriaCode} — {r.criteriaName} ({r.ruleType})
            </option>
          ))}
        </select>
      </div>

      {rule && <RuleConfigForm key={rule.id} rule={rule} />}
    </div>
  )
}

function RuleConfigForm({ rule }: { rule: RuleOut }) {
  const { t } = useTranslation()
  const updateRule = useUpdateRule()
  const [configText, setConfigText] = useState(() =>
    JSON.stringify(rule.config, null, 2)
  )
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  const handleSave = () => {
    setError(null)
    setSuccess(false)

    let config: Record<string, unknown>
    try {
      config = JSON.parse(configText)
    } catch {
      setError(t('admin.rules.invalidJson'))
      return
    }

    updateRule.mutate(
      { ruleId: rule.id, dto: { config } },
      {
        onSuccess: () => setSuccess(true),
        onError: (err) => {
          setError(
            err instanceof ApiError ? err.message : t('admin.rules.saveError')
          )
        },
      }
    )
  }

  return (
    <div className="space-y-4 rounded-md border p-4">
      <div className="flex items-center gap-4 text-sm">
        <div>
          <span className="text-muted-foreground">{t('admin.rules.ruleType')}: </span>
          <span className="font-mono">{rule.ruleType}</span>
        </div>
        <div>
          <span className="text-muted-foreground">{t('admin.rules.semester')}: </span>
          <span>{rule.semester}</span>
        </div>
        <div>
          <span className="text-muted-foreground">{t('admin.rules.priority')}: </span>
          <span>{rule.priority}</span>
        </div>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="configEditor">{t('admin.rules.config')}</Label>
        <Textarea
          id="configEditor"
          value={configText}
          onChange={(e) => setConfigText(e.target.value)}
          rows={10}
          className="font-mono text-xs"
        />
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}
      {success && (
        <p className="text-sm text-green-600">{t('admin.rules.saved')}</p>
      )}

      <Button onClick={handleSave} disabled={updateRule.isPending}>
        <Save className="h-3 w-3" />
        {updateRule.isPending ? t('common.submitting') : t('admin.rules.save')}
      </Button>
    </div>
  )
}
