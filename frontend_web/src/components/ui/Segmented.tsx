import { motion } from 'framer-motion'
import type { ReactNode } from 'react'
import { cn } from '../../lib/cn'

interface Option<T extends string> {
  value: T
  label: string
  icon?: ReactNode
}

interface SegmentedProps<T extends string> {
  options: Option<T>[]
  value: T
  onChange: (value: T) => void
  /** Unique per instance; drives the sliding highlight. */
  id: string
  size?: 'sm' | 'md'
  ariaLabel: string
  className?: string
}

export default function Segmented<T extends string>({
  options,
  value,
  onChange,
  id,
  size = 'md',
  ariaLabel,
  className,
}: SegmentedProps<T>) {
  return (
    <div
      role="radiogroup"
      aria-label={ariaLabel}
      className={cn('inline-flex rounded-xl border border-white/[0.08] bg-black/25 p-1', className)}
    >
      {options.map((opt) => {
        const active = opt.value === value
        return (
          <button
            key={opt.value}
            role="radio"
            aria-checked={active}
            type="button"
            onClick={() => onChange(opt.value)}
            className={cn(
              'relative inline-flex items-center justify-center gap-1.5 rounded-lg font-medium transition-colors',
              size === 'sm' ? 'h-7 px-3 text-xs' : 'h-8 px-3.5 text-[13px]',
              active ? 'text-fg' : 'text-fg-muted hover:text-fg',
            )}
          >
            {active && (
              <motion.span
                layoutId={`seg-${id}`}
                className="absolute inset-0 rounded-lg border border-white/10 bg-white/[0.09]"
                transition={{ type: 'spring', stiffness: 500, damping: 38 }}
              />
            )}
            <span className="relative flex items-center gap-1.5">
              {opt.icon}
              {opt.label}
            </span>
          </button>
        )
      })}
    </div>
  )
}
