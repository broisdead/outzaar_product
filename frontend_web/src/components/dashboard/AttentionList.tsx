import { ChevronRight } from 'lucide-react'
import type { AttentionItem } from '../../types'
import Avatar from '../ui/Avatar'
import Badge from '../ui/Badge'
import Skeleton from '../ui/Skeleton'

interface Props {
  items: AttentionItem[] | null
  onOpen: (conversationId: string) => void
}

export default function AttentionList({ items, onOpen }: Props) {
  return (
    <section className="glass rounded-[22px] p-6" aria-label="Needs attention">
      <div className="flex items-baseline justify-between">
        <h2 className="text-[17px] font-semibold tracking-[-0.01em] text-fg">Needs attention</h2>
        {items && <span className="text-xs text-fg-subtle">{items.length} conversations</span>}
      </div>

      {!items ? (
        <div className="mt-5 space-y-3" aria-busy>
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-[68px] w-full" />
          ))}
        </div>
      ) : (
        <ul className="mt-5 grid gap-3 lg:grid-cols-3">
          {items.map((item) => (
            <li key={item.conversationId}>
              <button
                type="button"
                onClick={() => onOpen(item.conversationId)}
                className="group flex h-full w-full flex-col rounded-2xl border border-white/[0.07] bg-white/[0.025] p-4 text-left transition-colors hover:border-white/[0.16] hover:bg-white/[0.05]"
              >
                <div className="flex items-center gap-3">
                  <Avatar name={item.name} />
                  <div className="min-w-0 flex-1 leading-tight">
                    <p className="truncate text-sm font-medium text-fg">{item.name}</p>
                    <p className="mt-0.5 truncate text-xs text-fg-muted">{item.company}</p>
                  </div>
                  <ChevronRight
                    size={16}
                    className="text-fg-subtle transition-transform group-hover:translate-x-0.5 group-hover:text-fg-muted"
                  />
                </div>
                <div className="mt-4">
                  <Badge tone={item.tone} dot>
                    {item.reason}
                  </Badge>
                </div>
                <p className="mt-2.5 text-[13px] text-fg-muted">{item.note}</p>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
