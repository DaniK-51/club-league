const SOFT_WARNING_DAYS = 7

export function isOverdue(activityDate: string): boolean {
  const date = new Date(activityDate)
  if (isNaN(date.getTime())) return false

  const deadline = new Date(date)
  deadline.setDate(deadline.getDate() + SOFT_WARNING_DAYS)

  return new Date() > deadline
}

export function toDateInputValue(date: Date = new Date()): string {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

export function toIsoString(dateInput: string): string {
  // dateInput is "YYYY-MM-DD" from <input type="date">
  // Interpret as noon Moscow time to avoid TZ edge cases
  return `${dateInput}T12:00:00+03:00`
}

export function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('ru-RU', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })
}
