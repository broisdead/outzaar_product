export const minutesAgo = (m: number): string =>
  new Date(Date.now() - m * 60_000).toISOString()

export function formatClock(iso: string): string {
  return new Date(iso).toLocaleTimeString('en-IN', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  })
}

export function formatRelative(iso: string): string {
  const mins = Math.round((Date.now() - new Date(iso).getTime()) / 60_000)
  if (mins < 1) return 'Just now'
  if (mins < 60) return `${mins} min ago`
  const hours = Math.round(mins / 60)
  if (hours < 24) return `${hours} h ago`
  const days = Math.round(hours / 24)
  return days === 1 ? 'Yesterday' : `${days} days ago`
}

// Short label for the conversation list: clock time today, otherwise day.
export function formatListTime(iso: string): string {
  const d = new Date(iso)
  const now = new Date()
  const sameDay = d.toDateString() === now.toDateString()
  if (sameDay) return formatClock(iso)
  const days = Math.round((now.getTime() - d.getTime()) / 86_400_000)
  if (days <= 1) return 'Yesterday'
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })
}

export function formatDayLabel(iso: string): string {
  const d = new Date(iso)
  const now = new Date()
  if (d.toDateString() === now.toDateString()) return 'Today'
  const y = new Date(now)
  y.setDate(now.getDate() - 1)
  if (d.toDateString() === y.toDateString()) return 'Yesterday'
  return d.toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'short' })
}

// The given weekday (0 = Sunday) in the calendar week after this one.
export function nextWeekWeekday(weekday: number): Date {
  const d = new Date()
  const untilNextMonday = ((8 - d.getDay()) % 7) || 7
  d.setDate(d.getDate() + untilNextMonday + ((weekday + 6) % 7))
  d.setHours(0, 0, 0, 0)
  return d
}
