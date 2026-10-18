import { SlidersHorizontal } from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import IcpInput from '../components/prospecting/IcpInput'
import IcpUnderstanding from '../components/prospecting/IcpUnderstanding'
import ProspectCard from '../components/prospecting/ProspectCard'
import ProspectDrawer from '../components/prospecting/ProspectDrawer'
import ProspectSkeleton from '../components/prospecting/ProspectSkeleton'
import ResultsToolbar, { type SortKey } from '../components/prospecting/ResultsToolbar'
import Button from '../components/ui/Button'
import EmptyState from '../components/ui/EmptyState'
import PageHeader from '../components/ui/PageHeader'
import { defaultIcpText } from '../data/icp'
import { analyzeIcp, getProspects, improveIcp } from '../services/api'
import type { IcpProfile, Prospect } from '../types'

export default function ProspectingPage() {
  const [text, setText] = useState(defaultIcpText)
  const [profile, setProfile] = useState<IcpProfile | null>(null)
  const [analyzing, setAnalyzing] = useState(true)
  const [improving, setImproving] = useState(false)
  const [flash, setFlash] = useState(false)

  const [prospects, setProspects] = useState<Prospect[] | null>(null)
  const [searching, setSearching] = useState(true)
  const [stale, setStale] = useState(false)

  const [minScore, setMinScore] = useState(70)
  const [city, setCity] = useState('all')
  const [sort, setSort] = useState<SortKey>('fit')

  const [openId, setOpenId] = useState<string | null>(null)
  const [queued, setQueued] = useState<Set<string>>(new Set())

  const resultsRef = useRef<HTMLElement>(null)

  // First load: understand the default ICP, then run the first search.
  useEffect(() => {
    let cancelled = false
    ;(async () => {
      const p = await analyzeIcp(defaultIcpText)
      if (cancelled) return
      setProfile(p)
      setAnalyzing(false)
      const found = await getProspects(p)
      if (cancelled) return
      setProspects(found)
      setSearching(false)
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const pulse = () => {
    setFlash(true)
    window.setTimeout(() => setFlash(false), 900)
  }

  const handleAnalyze = async () => {
    if (!text.trim()) return
    setAnalyzing(true)
    const p = await analyzeIcp(text)
    setProfile(p)
    setAnalyzing(false)
    setStale(prospects !== null)
  }

  const handleImprove = async () => {
    setImproving(true)
    const res = await improveIcp(text)
    setText(res.text)
    setProfile(res.profile)
    setImproving(false)
    setStale(prospects !== null)
    pulse()
  }

  const handleFind = async () => {
    if (!profile) return
    setSearching(true)
    setStale(false)
    setCity('all')
    window.setTimeout(
      () => resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }),
      60,
    )
    const found = await getProspects(profile)
    setProspects(found)
    setSearching(false)
  }

  const cities = useMemo(
    () => Array.from(new Set((prospects ?? []).map((p) => p.company.city))).sort(),
    [prospects],
  )

  const visible = useMemo(() => {
    const list = (prospects ?? []).filter(
      (p) => p.fitScore >= minScore && (city === 'all' || p.company.city === city),
    )
    return list.sort((a, b) =>
      sort === 'fit' ? b.fitScore - a.fitScore : a.company.name.localeCompare(b.company.name),
    )
  }, [prospects, minScore, city, sort])

  const open = prospects?.find((p) => p.id === openId) ?? null
  const closeDrawer = useCallback(() => setOpenId(null), [])
  const toggleQueue = useCallback((id: string) => {
    setQueued((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }, [])

  const hidden = (prospects?.length ?? 0) - visible.length

  return (
    <div className="mx-auto w-full max-w-[1120px] shrink-0 px-5 pb-16 pt-8 sm:px-8 lg:px-10 lg:pt-12">
      <PageHeader title="AI Prospecting" description="Tell OUTZAAR who you want to sell to." />

      <div className="mt-9 space-y-4">
        <IcpInput
          value={text}
          onChange={setText}
          onSubmit={handleAnalyze}
          busy={analyzing || improving}
          highlight={flash}
        />
        <IcpUnderstanding
          profile={profile}
          loading={analyzing}
          improving={improving}
          searching={searching}
          onImprove={handleImprove}
          onFind={handleFind}
        />
      </div>

      <section ref={resultsRef} className="mt-14 scroll-mt-8" aria-label="Prospects found">
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <h2 className="text-[22px] font-semibold tracking-[-0.02em] text-fg">Prospects found</h2>
          {!searching && prospects && (
            <p className="text-sm text-fg-muted">
              {visible.length} of {prospects.length} companies shown
            </p>
          )}
        </div>

        {stale && !searching && (
          <p className="mt-3 rounded-xl border border-brand-blue/25 bg-brand-blue/[0.07] px-4 py-2.5 text-[13px] text-[#B4C2FF]">
            Your ideal customer changed. Select Find Prospects to refresh these results.
          </p>
        )}

        {!searching && prospects && prospects.length > 0 && (
          <div className="mt-5">
            <ResultsToolbar
              minScore={minScore}
              onMinScore={setMinScore}
              city={city}
              cities={cities}
              onCity={setCity}
              sort={sort}
              onSort={setSort}
            />
          </div>
        )}

        <div className="mt-6">
          {searching ? (
            <div className="grid gap-4 lg:grid-cols-2" aria-busy aria-label="Searching for prospects">
              {[0, 1, 2, 3].map((i) => (
                <ProspectSkeleton key={i} />
              ))}
            </div>
          ) : prospects && prospects.length === 0 ? (
            <EmptyState
              icon={<SlidersHorizontal size={20} />}
              title="No matching companies in the demo data"
              description="The demo covers pharmaceutical, healthcare, industrial and chemical manufacturers. Adjust the description above, or pick one of the examples."
            />
          ) : visible.length === 0 ? (
            <EmptyState
              icon={<SlidersHorizontal size={20} />}
              title="No prospects match these filters"
              description={`${hidden} ${hidden === 1 ? 'company is' : 'companies are'} hidden by the current score and location filters.`}
              action={
                <Button
                  onClick={() => {
                    setMinScore(0)
                    setCity('all')
                  }}
                >
                  Reset filters
                </Button>
              }
            />
          ) : (
            <div className="grid gap-4 lg:grid-cols-2">
              {visible.map((p) => (
                <ProspectCard
                  key={p.id}
                  prospect={p}
                  queued={queued.has(p.id)}
                  onOpen={() => setOpenId(p.id)}
                />
              ))}
            </div>
          )}
        </div>
      </section>

      <ProspectDrawer
        prospect={open}
        queued={open ? queued.has(open.id) : false}
        onClose={closeDrawer}
        onToggleQueue={toggleQueue}
      />
    </div>
  )
}
