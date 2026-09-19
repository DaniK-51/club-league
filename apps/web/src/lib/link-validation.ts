// Client-side link validation mirrors backend whitelist (UX only — server is source of truth)
// Source: apps/api/.env.example ALLOWED_LINK_DOMAINS

const ALLOWED_DOMAINS = [
  'docs.google.com',
  'drive.google.com',
  't.me',
  'telegram.me',
  'telegram.dog',
  'vk.com',
  'm.vk.com',
  'youtu.be',
  'youtube.com',
  'disk.yandex.ru',
  'disk.yandex.com',
  'yadi.sk',
  'github.com',
  'github.io',
  'notion.so',
  'notion.site',
  'dropbox.com',
  'dropbox.tech',
  'innopolis.university',
  'www.innopolis.university',
]

export type LinkValidationResult =
  | { valid: true; domain: string }
  | { valid: false; error: 'INVALID_URL' | 'DOMAIN_NOT_ALLOWED' | 'DUPLICATE' }

export function validateLink(
  url: string,
  existingUrls: string[] = []
): LinkValidationResult {
  const trimmed = url.trim()
  if (!trimmed) {
    return { valid: false, error: 'INVALID_URL' }
  }

  let parsed: URL
  try {
    parsed = new URL(trimmed)
  } catch {
    return { valid: false, error: 'INVALID_URL' }
  }

  if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
    return { valid: false, error: 'INVALID_URL' }
  }

  const domain = parsed.hostname.toLowerCase()

  const allowed = ALLOWED_DOMAINS.some(
    (root) => domain === root || domain.endsWith(`.${root}`)
  )
  if (!allowed) {
    return { valid: false, error: 'DOMAIN_NOT_ALLOWED' }
  }

  const normalized = trimmed.replace(/\/+$/, '')
  const isDuplicate = existingUrls.some(
    (u) => u.replace(/\/+$/, '') === normalized
  )
  if (isDuplicate) {
    return { valid: false, error: 'DUPLICATE' }
  }

  return { valid: true, domain }
}

export function getDomain(url: string): string {
  try {
    return new URL(url).hostname.toLowerCase()
  } catch {
    return ''
  }
}
