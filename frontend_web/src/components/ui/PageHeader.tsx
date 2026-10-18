import type { ReactNode } from 'react'

interface PageHeaderProps {
  title: string
  description: string
  actions?: ReactNode
}

export default function PageHeader({ title, description, actions }: PageHeaderProps) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-[32px] font-semibold leading-[1.1] tracking-[-0.025em] text-fg sm:text-[38px]">
          {title}
        </h1>
        <p className="mt-2.5 max-w-xl text-[15px] leading-relaxed text-fg-muted">{description}</p>
      </div>
      {actions}
    </div>
  )
}
