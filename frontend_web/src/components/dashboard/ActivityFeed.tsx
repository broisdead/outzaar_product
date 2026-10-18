import { Calendar, Mail, Radar, Sparkles, Users } from 'lucide-react'
import type { ComponentType } from 'react'
import { formatRelative, minutesAgo } from '../../lib/time'
import type { Activity, ActivityKind } from '../../types'
import Skeleton from '../ui/Skeleton'

const icons: Record<ActivityKind, ComponentType<{ size?: number; strokeWidth?: number }>> = {
  prospect: Radar,
  contact: Users,
  message: Mail,
  analysis: Sparkles,
  meeting: Calendar,
}

interface Props {
  activities: Activity[] | null
}

export default function ActivityFeed({ activities }: Props) {
  return (
    <section className="glass rounded-[22px] p-6" aria-label="AI activity">
      <div className="flex items-center justify-between">
        <h2 className="text-[17px] font-semibold tracking-[-0.01em] text-fg">AI activity</h2>
        <span className="flex items-center gap-2 text-xs text-fg-muted">
          <span className="relative flex h-1.5 w-1.5">
            <span className="absolute inset-0 rounded-full bg-ok animate-beacon motion-reduce:animate-none" />
            <span className="relative h-1.5 w-1.5 rounded-full bg-ok" />
          </span>
          Working now
        </span>
      </div>

      {!activities ? (
        <div className="mt-6 space-y-5" aria-busy>
          {[0, 1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-9 w-full" />
          ))}
        </div>
      ) : (
        <ol className="relative mt-6">
          <span aria-hidden className="absolute bottom-3 left-[15px] top-3 w-px bg-white/[0.08]" />
          {activities.map((a) => {
            const Icon = icons[a.kind]
            return (
              <li key={a.id} className="relative flex items-start gap-4 pb-5 last:pb-0">
                <span className="relative z-10 flex h-[31px] w-[31px] shrink-0 items-center justify-center rounded-full border border-white/10 bg-ink-800 text-[#9DB0FF]">
                  <Icon size={14} strokeWidth={1.9} />
                </span>
                <div className="pt-1">
                  <p className="text-sm leading-snug text-fg">{a.text}</p>
                  <p className="mt-0.5 text-xs text-fg-subtle">{formatRelative(minutesAgo(a.minutesAgo))}</p>
                </div>
              </li>
            )
          })}
        </ol>
      )}
    </section>
  )
}
