import type { ReactNode } from 'react'
import { cn } from '../../lib/cn'

export type Tone = 'green' | 'blue' | 'violet' | 'amber' | 'red' | 'slate'

const tones: Record<Tone, { chip: string; dot: string }> = {
  green: { chip: 'bg-ok/10 text-ok border-ok/20', dot: 'bg-ok' },
  blue: { chip: 'bg-brand-blue/10 text-[#9DB0FF] border-brand-blue/25', dot: 'bg-brand-blue' },
  violet: { chip: 'bg-brand-violet/10 text-[#B7A5FB] border-brand-violet/25', dot: 'bg-brand-violet' },
  amber: { chip: 'bg-warn/10 text-warn border-warn/20', dot: 'bg-warn' },
  red: { chip: 'bg-bad/10 text-bad border-bad/20', dot: 'bg-bad' },
  slate: { chip: 'bg-white/[0.05] text-fg-muted border-white/10', dot: 'bg-fg-subtle' },
}

export function toneDot(tone: Tone): string {
  return tones[tone].dot
}

interface BadgeProps {
  tone?: Tone
  dot?: boolean
  children: ReactNode
  className?: string
}

export default function Badge({ tone = 'slate', dot, children, className }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium',
        tones[tone].chip,
        className,
      )}
    >
      {dot && <span className={cn('h-1.5 w-1.5 rounded-full', tones[tone].dot)} />}
      {children}
    </span>
  )
}
