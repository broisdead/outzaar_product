import type { ReactNode } from 'react'

interface EmptyStateProps {
  icon: ReactNode
  title: string
  description: string
  action?: ReactNode
}

export default function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="glass flex flex-col items-center rounded-2xl px-6 py-14 text-center">
      <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-xl border border-white/10 bg-white/[0.04] text-fg-muted">
        {icon}
      </div>
      <h3 className="text-[15px] font-medium text-fg">{title}</h3>
      <p className="mt-1.5 max-w-sm text-sm leading-relaxed text-fg-muted">{description}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}
