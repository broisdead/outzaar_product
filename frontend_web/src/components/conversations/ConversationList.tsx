import { motion } from 'framer-motion'
import { Inbox, Search } from 'lucide-react'
import { useMemo, useState } from 'react'
import { statusMeta } from '../../data/conversations'
import { cn } from '../../lib/cn'
import { formatListTime } from '../../lib/time'
import type { Conversation } from '../../types'
import Avatar from '../ui/Avatar'
import { toneDot } from '../ui/Badge'
import Segmented from '../ui/Segmented'
import Skeleton from '../ui/Skeleton'

type Tab = 'all' | 'action' | 'waiting'

interface Props {
  conversations: Conversation[] | null
  selectedId: string | null
  onSelect: (id: string) => void
  className?: string
}

const needsAction = (c: Conversation) => ['meeting', 'interested', 'followup'].includes(c.status)

export default function ConversationList({ conversations, selectedId, onSelect, className }: Props) {
  const [query, setQuery] = useState('')
  const [tab, setTab] = useState<Tab>('all')

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return (conversations ?? []).filter((c) => {
      if (tab === 'action' && !needsAction(c)) return false
      if (tab === 'waiting' && needsAction(c)) return false
      if (!q) return true
      return (
        c.contact.name.toLowerCase().includes(q) ||
        c.company.toLowerCase().includes(q) ||
        c.messages.some((m) => m.body.toLowerCase().includes(q))
      )
    })
  }, [conversations, query, tab])

  return (
    <aside
      aria-label="Conversations"
      className={cn('glass min-h-0 flex-col overflow-hidden rounded-[22px]', className)}
    >
      <div className="px-4 pb-3 pt-5">
        <div className="flex items-baseline justify-between">
          <h1 className="text-[20px] font-semibold tracking-[-0.02em] text-fg">Conversations</h1>
          {conversations && <span className="text-xs text-fg-subtle">{conversations.length} active</span>}
        </div>

        <div className="relative mt-4">
          <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-fg-subtle" />
          <label htmlFor="conv-search" className="sr-only">
            Search conversations
          </label>
          <input
            id="conv-search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search people or companies"
            className="field h-9 w-full rounded-xl pl-9 pr-3 text-[13px]"
          />
        </div>

        <Segmented<Tab>
          id="conv-tab"
          ariaLabel="Filter conversations"
          size="sm"
          value={tab}
          onChange={setTab}
          className="mt-3 w-full [&>button]:flex-1"
          options={[
            { value: 'all', label: 'All' },
            { value: 'action', label: 'Needs action' },
            { value: 'waiting', label: 'Waiting' },
          ]}
        />
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-2 pb-2">
        {!conversations ? (
          <div className="space-y-1 px-2 pt-2" aria-busy>
            {[0, 1, 2, 3, 4].map((i) => (
              <div key={i} className="flex gap-3 rounded-xl p-3">
                <Skeleton className="h-10 w-10 shrink-0 rounded-full" />
                <div className="flex-1 space-y-2 pt-0.5">
                  <Skeleton className="h-3.5 w-32" />
                  <Skeleton className="h-3 w-44" />
                  <Skeleton className="h-3 w-24" />
                </div>
              </div>
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center px-6 py-14 text-center">
            <Inbox size={22} className="text-fg-subtle" />
            <p className="mt-3 text-sm font-medium text-fg">Nothing here</p>
            <p className="mt-1 text-[13px] text-fg-muted">No conversations match this search or filter.</p>
          </div>
        ) : (
          <ul className="space-y-0.5">
            {filtered.map((c) => {
              const meta = statusMeta[c.status]
              const last = c.messages[c.messages.length - 1]
              const active = c.id === selectedId
              return (
                <li key={c.id}>
                  <button
                    type="button"
                    onClick={() => onSelect(c.id)}
                    aria-current={active}
                    className={cn(
                      'relative flex w-full gap-3 rounded-xl px-3 py-3 text-left transition-colors',
                      active ? 'bg-white/[0.07]' : 'hover:bg-white/[0.035]',
                    )}
                  >
                    {active && (
                      <motion.span
                        layoutId="conv-active"
                        className="absolute inset-y-3 left-0 w-[2.5px] rounded-full bg-brand-blue"
                      />
                    )}
                    <Avatar name={c.contact.name} statusClass={toneDot(meta.tone)} />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-baseline justify-between gap-2">
                        <span
                          className={cn(
                            'truncate text-[14px] text-fg',
                            c.unread ? 'font-semibold' : 'font-medium',
                          )}
                        >
                          {c.contact.name}
                        </span>
                        <span className="shrink-0 text-[11px] tabular-nums text-fg-subtle">
                          {formatListTime(last.sentAt)}
                        </span>
                      </div>
                      <p className="truncate text-xs text-fg-muted">{c.company}</p>
                      <p
                        className={cn(
                          'mt-1 truncate text-[13px]',
                          c.unread ? 'text-fg' : 'text-fg-subtle',
                        )}
                      >
                        {last.sender === 'outzaar' ? 'You: ' : ''}
                        {last.body}
                      </p>
                      <div className="mt-1.5 flex items-center justify-between">
                        <span className="inline-flex items-center gap-1.5 text-xs text-fg-muted">
                          <span className={cn('h-1.5 w-1.5 rounded-full', toneDot(meta.tone))} />
                          {meta.label}
                        </span>
                        {c.unread && <span className="h-2 w-2 rounded-full bg-brand-blue" aria-label="Unread" />}
                      </div>
                    </div>
                  </button>
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </aside>
  )
}
