import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import ActivityFeed from '../components/dashboard/ActivityFeed'
import AttentionList from '../components/dashboard/AttentionList'
import MetricStrip from '../components/dashboard/MetricStrip'
import PipelineFunnel from '../components/dashboard/PipelineFunnel'
import PageHeader from '../components/ui/PageHeader'
import Segmented from '../components/ui/Segmented'
import { getDashboard } from '../services/api'
import type { DashboardData, DashboardRange } from '../types'

export default function DashboardPage() {
  const navigate = useNavigate()
  const [data, setData] = useState<DashboardData | null>(null)
  const [range, setRange] = useState<DashboardRange>('30d')

  useEffect(() => {
    let cancelled = false
    getDashboard().then((d) => {
      if (!cancelled) setData(d)
    })
    return () => {
      cancelled = true
    }
  }, [])

  const snapshot = data?.ranges[range] ?? null

  return (
    <div className="mx-auto w-full max-w-[1240px] shrink-0 px-5 pb-16 pt-8 sm:px-8 lg:px-10 lg:pt-12">
      <PageHeader
        title="OUTZAAR AI Operations"
        description="Your outbound sales operation at a glance."
        actions={
          <Segmented<DashboardRange>
            id="dash-range"
            ariaLabel="Time range"
            value={range}
            onChange={setRange}
            options={[
              { value: '7d', label: 'Last 7 days' },
              { value: '30d', label: 'Last 30 days' },
            ]}
          />
        }
      />

      <div className="mt-9 space-y-4">
        <MetricStrip metrics={snapshot?.metrics ?? null} range={range} />

        <div className="grid gap-4 xl:grid-cols-[1.55fr_1fr]">
          <PipelineFunnel stages={snapshot?.pipeline ?? null} />
          <ActivityFeed activities={data?.activities ?? null} />
        </div>

        <AttentionList
          items={data?.attention ?? null}
          onOpen={(id) => navigate(`/conversations?c=${id}`)}
        />
      </div>
    </div>
  )
}
