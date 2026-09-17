import { ExternalLink } from 'lucide-react'
import type { ReportLink } from '@/lib/types'

interface ReportLinksProps {
  links: ReportLink[]
  className?: string
}

export function ReportLinks({ links, className }: ReportLinksProps) {
  if (!links.length) return null

  return (
    <div className={className ?? 'flex flex-wrap gap-1'}>
      {links.map((link, i) => (
        <a
          key={i}
          href={link.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-muted-foreground hover:underline"
        >
          <ExternalLink className="inline h-3 w-3" /> {link.domain}
        </a>
      ))}
    </div>
  )
}
