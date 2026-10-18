import { motion } from 'framer-motion'
import { useState } from 'react'
import { cn } from '../../lib/cn'
import type { PipelineStage } from '../../types'
import Skeleton from '../ui/Skeleton'

interface Props {
  stages: PipelineStage[] | null
}

const fills = [
  'linear-gradient(90deg, rgba(91,124,255,0.75), rgba(91,124,255,0.45))',
  'linear-gradient(90deg, rgba(96,120,250,0.75), rgba(112,112,246,0.45))',
  'linear-gradient(90deg, rgba(107,111,245,0.8), rgba(125,106,246,0.5))',
  'linear-gradient(90deg, rgba(122,106,246,0.85), rgba(139,108,246,0.55))',
  'linear-gradient(90deg, #3DD6A0, rgba(61,214,160,0.55))',
]

export default function PipelineFunnel({ stages }: Props) {
  const [selected, setSelected] = useState<string | null>(null)

  return (
    <section className="glass rounded-[22px] p-6" aria-label="Outbound pipeline">
      <h2 className="text-[17px] font-semibold tracking-[-0.01em] text-fg">Outbound pipeline</h2>
      <p className="mt-1 text-[13px] text-fg-muted">From matching company to booked meeting. Select a stage for detail.</p>

      {!stages ? (
        <div className="mt-6 space-y-4" aria-busy>
          {[0, 1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-11 w-full" />
          ))}
        </div>
      ) : (
        <ul className="mt-6 space-y-2">
          {stages.map((s, i) => {
            const first = stages[0].count
            const prev = stages[i - 1]
            const next = stages[i + 1]
            const pct = Math.max((s.count / first) * 100, 4)
            const active = selected === s.id
            const fromPrev = prev ? Math.round((s.count / prev.count) * 100) : null
            const overall = Math.round((s.count / first) * 100)
            const onward = next ? Math.round((next.count / s.count) * 100) : null

            return (
              <li key={s.id}>
                <button
                  type="button"
                  onClick={() => setSelected(active ? null : s.id)}
                  aria-expanded={active}
                  className={cn(
                    'grid w-full grid-cols-[1fr_auto] items-center gap-x-4 gap-y-2 rounded-xl px-3 py-2.5 text-left transition-colors sm:grid-cols-[150px_1fr_auto]',
                    active ? 'bg-white/[0.05]' : 'hover:bg-white/[0.03]',
                  )}
                >
                  <span className="text-sm font-medium text-fg">{s.label}</span>
                  <span className="text-right sm:order-3 sm:w-[110px]">
                    <span className="text-[15px] font-semibold tabular-nums text-fg">{s.count.toLocaleString('en-IN')}</span>
                    {fromPrev !== null && (
                      <span className="ml-2 text-xs tabular-nums text-fg-subtle">{fromPrev}%</span>
                    )}
                  </span>
                  <span className="col-span-2 h-8 overflow-hidden rounded-lg bg-white/[0.04] sm:order-2 sm:col-span-1">
                    <motion.span
                      className="block h-full rounded-lg"
                      style={{ background: fills[Math.min(i, fills.length - 1)] }}
                      initial={{ width: 0 }}
                      animate={{ width: `${pct}%` }}
                      transition={{ duration: 0.8, delay: i * 0.07, ease: [0.22, 1, 0.36, 1] }}
                    />
                  </span>
                </button>
                {active && (
                  <motion.p
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="mx-3 mb-1 mt-1 rounded-lg border border-white/[0.06] bg-black/20 px-3.5 py-3 text-[13px] leading-relaxed text-fg-muted"
                  >
                    {s.description}. {s.count} of {first} prospects reached this stage ({overall}%).{' '}
                    {onward !== null
                      ? `${onward}% of them moved on to ${next!.label.toLowerCase()}.`
                      : 'This is the last stage of the pipeline.'}
                  </motion.p>
                )}
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
