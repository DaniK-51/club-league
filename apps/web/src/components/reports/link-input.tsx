import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { X, Plus, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { validateLink, getDomain } from '@/lib/link-validation'
import { cn } from '@/lib/utils'

interface LinkInputProps {
  links: string[]
  onChange: (links: string[]) => void
}

export function LinkInput({ links, onChange }: LinkInputProps) {
  const { t } = useTranslation()
  const [inputValue, setInputValue] = useState('')
  const [error, setError] = useState<string | null>(null)

  const addLink = () => {
    const result = validateLink(inputValue, links)
    if (!result.valid) {
      if (result.error === 'INVALID_URL') setError(t('report.linkErrors.invalidUrl'))
      else if (result.error === 'DOMAIN_NOT_ALLOWED') setError(t('report.linkErrors.domainNotAllowed'))
      else if (result.error === 'DUPLICATE') setError(t('report.linkErrors.duplicate'))
      return
    }
    setError(null)
    onChange([...links, inputValue.trim()])
    setInputValue('')
  }

  const removeLink = (index: number) => {
    onChange(links.filter((_, i) => i !== index))
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      addLink()
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <Input
          value={inputValue}
          onChange={(e) => {
            setInputValue(e.target.value)
            setError(null)
          }}
          onKeyDown={handleKeyDown}
          placeholder={t('report.linkPlaceholder')}
          className={cn(error && 'border-destructive')}
        />
        <Button type="button" variant="outline" size="icon" onClick={addLink}>
          <Plus className="h-4 w-4" />
        </Button>
      </div>

      {error && (
        <p className="flex items-center gap-1 text-sm text-destructive">
          <AlertCircle className="h-3 w-3" />
          {error}
        </p>
      )}

      {links.length > 0 && (
        <ul className="space-y-1">
          {links.map((link, i) => (
            <li
              key={i}
              className="flex items-center justify-between rounded-md border bg-muted/50 px-3 py-1.5 text-sm"
            >
              <span className="truncate">
                <span className="text-muted-foreground">{getDomain(link)}</span>
                {' — '}
                <span className="text-xs">{link}</span>
              </span>
              <button
                type="button"
                onClick={() => removeLink(i)}
                className="ml-2 shrink-0 text-muted-foreground hover:text-destructive"
              >
                <X className="h-3 w-3" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
