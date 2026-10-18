import { Check, Globe, MapPin, Plus } from 'lucide-react'
import { useRef, type ReactNode } from 'react'
import type { Prospect } from '../../types'
import Avatar from '../ui/Avatar'
import Badge from '../ui/Badge'
import Button from '../ui/Button'
import Drawer from '../ui/Drawer'
import ScoreRing, { scoreColor } from '../ui/ScoreRing'

interface Props {
  prospect: Prospect | null
  queued: boolean
  onClose: () => void
  onToggleQueue: (id: string) => void
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="border-t border-white/[0.06] px-7 py-6">
      <h3 className="text-[15px] font-medium text-fg">{title}</h3>
      <div className="mt-3.5">{children}</div>
    </section>
  )
}

export default function ProspectDrawer({ prospect: current, queued, onClose, onToggleQueue }: Props) {
  // Keep the last prospect around so the panel content stays put while it slides out.
  const last = useRef<Prospect | null>(null)
  if (current) last.current = current
  const prospect = current ?? last.current

  return (
    <Drawer open={!!current} onClose={onClose} label={prospect ? `${prospect.company.name} details` : 'Company details'}>
      {prospect && (
        <>
          <div className="min-h-0 flex-1 overflow-y-auto">
            <header className="px-7 pb-7 pt-7">
              <div className="flex items-start gap-4 pr-10">
                <Avatar name={prospect.company.name} shape="square" size="lg" />
                <div className="min-w-0 flex-1">
                  <h2 className="text-[24px] font-semibold leading-tight tracking-[-0.02em] text-fg">
                    {prospect.company.name}
                  </h2>
                  <p className="mt-1 text-sm text-fg-muted">{prospect.company.industry}</p>
                </div>
              </div>
              <div className="mt-5 flex items-center justify-between gap-4">
                <div className="flex flex-wrap gap-x-5 gap-y-1.5 text-[13px] text-fg-muted">
                  <span className="inline-flex items-center gap-1.5">
                    <MapPin size={13} className="text-fg-subtle" />
                    {prospect.company.city}, {prospect.company.state}
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    <Globe size={13} className="text-fg-subtle" />
                    {prospect.company.website}
                  </span>
                </div>
                <ScoreRing score={prospect.fitScore} size={64} label />
              </div>
            </header>

            <Section title="Company overview">
              <p className="text-sm leading-relaxed text-fg-muted">{prospect.company.description}</p>
              <dl className="mt-5 grid grid-cols-2 gap-4 sm:grid-cols-4">
                {[
                  ['Employees', prospect.company.employeeRange],
                  ['Founded', String(prospect.company.founded)],
                  ['Revenue', prospect.company.revenue],
                  ['Facilities', String(prospect.company.facilities)],
                ].map(([k, v]) => (
                  <div key={k}>
                    <dt className="text-xs text-fg-subtle">{k}</dt>
                    <dd className="mt-1 text-sm font-medium text-fg">{v}</dd>
                  </div>
                ))}
              </dl>
            </Section>

            <Section title="Why OUTZAAR identified them">
              <p className="text-sm leading-relaxed text-fg-muted">{prospect.whyIdentified}</p>
            </Section>

            <Section title="How the fit score was reached">
              <ul className="space-y-4">
                {prospect.fitReasoning.map((f) => (
                  <li key={f.label}>
                    <div className="flex items-baseline justify-between text-sm">
                      <span className="text-fg">{f.label}</span>
                      <span className="tabular-nums text-fg-muted">{f.score}</span>
                    </div>
                    <div className="mt-1.5 h-1 overflow-hidden rounded-full bg-white/[0.07]">
                      <div
                        className="h-full rounded-full"
                        style={{ width: `${f.score}%`, background: scoreColor(f.score) }}
                      />
                    </div>
                    <p className="mt-1.5 text-[13px] text-fg-subtle">{f.note}</p>
                  </li>
                ))}
              </ul>
            </Section>

            <Section title="Buying signals">
              <div className="flex flex-wrap gap-2">
                {prospect.signals.map((s) => (
                  <Badge key={s} tone="green" dot>
                    {s}
                  </Badge>
                ))}
              </div>
            </Section>

            <Section title="Likely pain points">
              <ul className="space-y-2.5">
                {prospect.painPoints.map((p) => (
                  <li key={p} className="flex gap-3 text-sm leading-relaxed text-fg-muted">
                    <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-warn" />
                    {p}
                  </li>
                ))}
              </ul>
            </Section>

            <Section title="Decision makers">
              <ul className="space-y-3">
                {prospect.decisionMakers.map((dm) => (
                  <li
                    key={dm.id}
                    className="flex gap-3.5 rounded-xl border border-white/[0.07] bg-white/[0.025] p-3.5"
                  >
                    <Avatar name={dm.name} />
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-fg">{dm.name}</p>
                      <p className="text-[13px] text-fg-muted">{dm.title}</p>
                      <p className="mt-1.5 text-[13px] leading-relaxed text-fg-subtle">{dm.note}</p>
                    </div>
                  </li>
                ))}
              </ul>
            </Section>

            <section className="px-7 pb-8 pt-6">
              <div className="rounded-2xl border border-brand-blue/25 bg-gradient-to-br from-brand-blue/[0.10] to-brand-violet/[0.07] p-5">
                <h3 className="text-[15px] font-medium text-fg">Recommended outreach angle</h3>
                <p className="mt-2.5 text-sm leading-relaxed text-fg-muted">{prospect.outreachAngle}</p>
              </div>
            </section>
          </div>

          <footer className="flex items-center justify-between gap-3 border-t border-white/[0.07] bg-ink-900/70 px-7 py-4">
            <Button variant="ghost" onClick={onClose}>
              Close
            </Button>
            <Button
              variant={queued ? 'secondary' : 'primary'}
              icon={queued ? <Check size={16} /> : <Plus size={16} />}
              onClick={() => onToggleQueue(prospect.id)}
            >
              {queued ? 'Queued for outreach' : 'Add to outreach'}
            </Button>
          </footer>
        </>
      )}
    </Drawer>
  )
}
