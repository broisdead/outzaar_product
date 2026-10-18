import { ChevronDown } from 'lucide-react'
import Segmented from '../ui/Segmented'

export type SortKey = 'fit' | 'name'

interface Props {
  minScore: number
  onMinScore: (n: number) => void
  city: string
  cities: string[]
  onCity: (c: string) => void
  sort: SortKey
  onSort: (s: SortKey) => void
}

export default function ResultsToolbar({ minScore, onMinScore, city, cities, onCity, sort, onSort }: Props) {
  return (
    <div className="flex flex-wrap items-center gap-x-8 gap-y-4">
      <div className="flex items-center gap-3.5">
        <label htmlFor="min-score" className="text-[13px] text-fg-muted">
          Minimum fit score
        </label>
        <input
          id="min-score"
          type="range"
          min={0}
          max={100}
          step={1}
          value={minScore}
          onChange={(e) => onMinScore(Number(e.target.value))}
          className="oz-range w-36"
        />
        <span className="w-7 text-sm font-medium tabular-nums text-fg">{minScore}</span>
      </div>

      <div className="relative">
        <label htmlFor="city-filter" className="sr-only">
          Location
        </label>
        <select
          id="city-filter"
          value={city}
          onChange={(e) => onCity(e.target.value)}
          className="field h-9 appearance-none rounded-xl pl-3.5 pr-9 text-[13px]"
        >
          <option value="all" className="bg-ink-800">
            All locations
          </option>
          {cities.map((c) => (
            <option key={c} value={c} className="bg-ink-800">
              {c}
            </option>
          ))}
        </select>
        <ChevronDown size={15} className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-fg-subtle" />
      </div>

      <Segmented<SortKey>
        id="prospect-sort"
        ariaLabel="Sort prospects"
        size="sm"
        value={sort}
        onChange={onSort}
        options={[
          { value: 'fit', label: 'Best fit' },
          { value: 'name', label: 'Name' },
        ]}
        className="sm:ml-auto"
      />
    </div>
  )
}
