import { TrendingDown, TrendingUp } from 'lucide-react'
import { cn } from '../../lib/cn'
import type { DashboardMetric, DashboardRange } from '../../types'
import Skeleton from '../ui/Skeleton'
import Sparkline from './Sparkline'

interface Props {
  metrics: DashboardMetric[] | null
  range: DashboardRange
}

export default function MetricStrip({ metrics, range }: Props) {
  const cells: Array<DashboardMetric | null> = metrics ?? [null, null, null, null, null]
  const compare = range === '7d' ? 'vs previous 7 days' : 'vs previous 30 days'

  return (
    <section
      aria-label="Key metrics"
      className="grid grid-cols-2 gap-px overflow-hidden rounded-[22px] border border-white/[0.07] bg-white/[0.06] md:grid-cols-3 xl:grid-cols-5"
    >
      {cells.map((m, i) => {
        if (!m) {
          return (
            <div key={i} className="bg-ink-900/95 p-5" aria-busy>
              <Skeleton className="h-3 w-24" />
              <Skeleton className="mt-4 h-9 w-16" />
              <Skeleton className="mt-4 h-3 w-28" />
            </div>
          )
        }
        const metric = m
        const up = metric.delta >= 0
        const color = up ? '#3DD6A0' : '#F0708A'
        return (
          <div
            key={metric.id}
            className={cn(
              'bg-ink-900/95 p-5',
              // Fifth cell spans the row on the two-column layout so nothing is left dangling.
              i === 4 && 'col-span-2 md:col-span-1',
            )}
          >
            <p className="text-[13px] text-fg-muted">{metric.label}</p>
            <div className="mt-3 flex items-end justify-between gap-2">
              <p className="text-[36px] font-semibold leading-none tracking-[-0.03em] tabular-nums text-fg">
                {metric.value.toLocaleString('en-IN')}
              </p>
              <Sparkline series={metric.series} color={color} />
            </div>
            <p className="mt-4 flex items-center gap-1.5 text-xs">
              {up ? <TrendingUp size={13} style={{ color }} /> : <TrendingDown size={13} style={{ color }} />}
              <span className="font-medium tabular-nums" style={{ color }}>
                {up ? '+' : ''}
                {metric.delta}
              </span>
              <span className="text-fg-subtle">{compare}</span>
            </p>
          </div>
        )
      })}
    </section>
  )
}
