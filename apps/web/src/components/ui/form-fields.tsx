import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { cn } from '@/lib/utils'

// === NumberField ===

interface NumberFieldProps {
  label: string
  value: number | ''
  onChange: (v: number) => void
  min?: number
  max?: number
  id?: string
}

export function NumberField({ label, value, onChange, min, max, id }: NumberFieldProps) {
  return (
    <div className="space-y-1.5">
      {id ? <Label htmlFor={id}>{label}</Label> : <Label>{label}</Label>}
      <Input
        id={id}
        type="number"
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        min={min}
        max={max}
      />
    </div>
  )
}

// === SelectField ===

interface SelectFieldProps {
  label: string
  value: string
  options: { value: string; label: string }[]
  onChange: (v: string) => void
  id?: string
}

export function SelectField({ label, value, options, onChange, id }: SelectFieldProps) {
  return (
    <div className="space-y-1.5">
      {id ? <Label htmlFor={id}>{label}</Label> : <Label>{label}</Label>}
      <select
        id={id}
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

// === CheckboxField ===

interface CheckboxFieldProps {
  label: string
  value: boolean
  onChange: (v: boolean) => void
  className?: string
}

export function CheckboxField({ label, value, onChange, className }: CheckboxFieldProps) {
  return (
    <label className={cn('flex items-center gap-2 text-sm', className)}>
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
