import { Check, ChevronRight, Globe, MapPin, Users } from 'lucide-react'
import type { KeyboardEvent } from 'react'
import type { Prospect } from '../../types'
import Avatar from '../ui/Avatar'
import Badge from '../ui/Badge'
import ScoreRing from '../ui/ScoreRing'

interface Props {
  prospect: Prospect
  queued: boolean
  onOpen: () => void
}

export default function ProspectCard({ prospect, queued, onOpen }: Props) {
  const { company, decisionMakers } = prospect
  const lead = decisionMakers[0]

  const onKey = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      onOpen()
    }
  }

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onOpen}
      onKeyDown={onKey}
      aria-label={`Open details for ${company.name}`}
      className="glass group flex cursor-pointer flex-col rounded-[20px] p-5 text-left transition-colors duration-150 hover:border-white/[0.16] hover:bg-white/[0.045]"
    >
      <div className="flex items-start gap-3.5">
        <Avatar name={company.name} shape="square" size="lg" />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className="truncate text-[16px] font-medium leading-tight tracking-[-0.01em] text-fg">
              {company.name}
            </h3>
            {queued && (
              <Badge tone="green" className="shrink-0">
                <Check size={11} /> Queued
              </Badge>
            )}
          </div>
          <p className="mt-1 text-[13px] text-fg-muted">{company.industry}</p>
        </div>
        <ScoreRing score={prospect.fitScore} size={52} />
      </div>

      <div className="mt-4 flex flex-wrap gap-x-4 gap-y-1.5 text-[13px] text-fg-muted">
        <span className="inline-flex items-center gap-1.5">
          <MapPin size={13} className="text-fg-subtle" />
          {company.city}, {company.state}
        </span>
        <span className="inline-flex items-center gap-1.5">
          <Users size={13} className="text-fg-subtle" />
          {company.employeeRange} employees
        </span>
        <span className="inline-flex items-center gap-1.5">
          <Globe size={13} className="text-fg-subtle" />
          {company.website}
        </span>
      </div>

      <p className="mt-3.5 line-clamp-2 text-sm leading-relaxed text-fg-muted">{company.description}</p>

      <div className="mt-4 flex flex-wrap gap-1.5">
        {prospect.signals.map((s) => (
          <span
            key={s}
            className="inline-flex items-center gap-1 rounded-lg bg-ok/[0.08] px-2 py-1 text-xs text-ok"
          >
            <span aria-hidden className="text-[13px] leading-none">+</span>
            {s}
          </span>
        ))}
      </div>

      <p className="mt-3.5 text-[13px] leading-snug text-fg-subtle">
        <span className="text-fg-muted">Likely pain: </span>
        {prospect.painPoints[0]}
      </p>

      <div className="mt-auto pt-5">
        <div className="flex items-center gap-3 border-t border-white/[0.06] pt-4">
          <Avatar name={lead.name} size="sm" />
          <div className="min-w-0 flex-1 leading-tight">
            <p className="truncate text-[13px] font-medium text-fg">{lead.name}</p>
            <p className="truncate text-xs text-fg-subtle">{lead.title}</p>
          </div>
          {decisionMakers.length > 1 && (
            <span className="text-xs text-fg-subtle">+{decisionMakers.length - 1} more</span>
          )}
          <ChevronRight
            size={16}
            className="text-fg-subtle transition-transform group-hover:translate-x-0.5 group-hover:text-fg-muted"
          />
        </div>
      </div>
    </div>
  )
}
