import { motion } from 'framer-motion'
import { Search, Sparkles } from 'lucide-react'
import type { IcpProfile } from '../../types'
import Button from '../ui/Button'
import Skeleton from '../ui/Skeleton'
import { LogoMark } from '../ui/Logo'

interface Props {
  profile: IcpProfile | null
  loading: boolean
  improving: boolean
  searching: boolean
  onImprove: () => void
  onFind: () => void
}

const container = { hidden: {}, show: { transition: { staggerChildren: 0.05 } } }
const item = {
  hidden: { opacity: 0, y: 6 },
  show: { opacity: 1, y: 0, transition: { duration: 0.3 } },
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <motion.div variants={item}>
      <dt className="text-xs text-fg-subtle">{label}</dt>
      <dd className="mt-1 text-[15px] font-medium leading-snug text-fg">{value}</dd>
    </motion.div>
  )
}

export default function IcpUnderstanding({
  profile,
  loading,
  improving,
  searching,
  onImprove,
  onFind,
}: Props) {
  const unrecognised = profile?.industryKeys.length === 0

  return (
    <section aria-label="What OUTZAAR understands" className="glass rounded-[22px] p-5 sm:p-6">
      <div className="flex items-center gap-2.5">
        <LogoMark size={24} />
        <h2 className="text-[15px] font-medium text-fg">OUTZAAR understands</h2>
        {(loading || improving) && (
          <span className="ml-1 text-xs text-fg-subtle">Reading your description...</span>
        )}
      </div>

      {loading || !profile ? (
        <div className="mt-6 grid gap-6 md:grid-cols-[1.1fr_1fr]" aria-busy>
          <div className="grid grid-cols-2 gap-5">
            {[0, 1, 2, 3].map((i) => (
              <div key={i}>
                <Skeleton className="h-3 w-16" />
                <Skeleton className="mt-2.5 h-5 w-32" />
              </div>
            ))}
          </div>
          <div className="space-y-3">
            <Skeleton className="h-3 w-28" />
            <Skeleton className="h-7 w-64" />
            <Skeleton className="h-3 w-24" />
            <Skeleton className="h-7 w-72" />
          </div>
        </div>
      ) : (
        <motion.div
          key={JSON.stringify(profile)}
          variants={container}
          initial="hidden"
          animate="show"
          className="mt-6 grid gap-7 md:grid-cols-[1.1fr_1fr]"
        >
          <dl className="grid grid-cols-2 gap-x-6 gap-y-5">
            <Fact label="Industry" value={profile.industry} />
            <Fact label="Location" value={profile.location} />
            <Fact label="Company size" value={profile.companySize} />
            <Fact label="Potential need" value={profile.potentialNeed} />
          </dl>

          <div className="space-y-5">
            <motion.div variants={item}>
              <p className="text-xs text-fg-subtle">Likely decision makers</p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {profile.decisionMakers.map((r) => (
                  <span
                    key={r}
                    className="rounded-lg border border-brand-violet/25 bg-brand-violet/10 px-2.5 py-1 text-[13px] text-[#C3B5FB]"
                  >
                    {r}
                  </span>
                ))}
              </div>
            </motion.div>
            <motion.div variants={item}>
              <p className="text-xs text-fg-subtle">Buying signals</p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {profile.buyingSignals.map((s) => (
                  <span
                    key={s}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-white/[0.08] bg-white/[0.03] px-2.5 py-1 text-[13px] text-fg-muted"
                  >
                    <span className="h-1.5 w-1.5 rounded-full bg-ok" />
                    {s}
                  </span>
                ))}
              </div>
            </motion.div>
          </div>
        </motion.div>
      )}

      {unrecognised && !loading && (
        <p className="mt-5 rounded-xl border border-warn/20 bg-warn/[0.06] px-3.5 py-2.5 text-[13px] text-warn">
          The demo data does not cover this segment yet. Try one of the examples above, or search anyway to see the empty state.
        </p>
      )}

      <div className="mt-6 flex flex-wrap items-center justify-end gap-3 border-t border-white/[0.06] pt-5">
        <Button
          variant="secondary"
          icon={<Sparkles size={16} />}
          onClick={onImprove}
          loading={improving}
          disabled={loading || searching}
        >
          Improve ICP
        </Button>
        <Button
          variant="primary"
          size="lg"
          icon={<Search size={17} />}
          onClick={onFind}
          loading={searching}
          disabled={loading || improving || !profile}
        >
          Find Prospects
        </Button>
      </div>
    </section>
  )
}
