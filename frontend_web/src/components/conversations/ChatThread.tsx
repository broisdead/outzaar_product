import { ArrowLeft, Sparkles } from 'lucide-react'
import { Fragment, useEffect, useRef, type RefObject } from 'react'
import { statusMeta } from '../../data/conversations'
import { formatDayLabel } from '../../lib/time'
import type { Channel, Conversation } from '../../types'
import Avatar from '../ui/Avatar'
import Badge, { toneDot } from '../ui/Badge'
import Button from '../ui/Button'
import Composer from './Composer'
import MessageBubble from './MessageBubble'

interface Props {
  conversation: Conversation
  channel: Channel
  onChannel: (c: Channel) => void
  draft: string
  onDraft: (v: string) => void
  onSend: () => void
  suggestion?: string
  textareaRef: RefObject<HTMLTextAreaElement>
  onBack: () => void
  onOpenInsights?: () => void
  freshIds: Set<string>
}

export default function ChatThread({
  conversation,
  channel,
  onChannel,
  draft,
  onDraft,
  onSend,
  suggestion,
  textareaRef,
  onBack,
  onOpenInsights,
  freshIds,
}: Props) {
  const scroller = useRef<HTMLDivElement>(null)
  const lastId = useRef(conversation.id)
  const meta = statusMeta[conversation.status]
  const firstName = conversation.contact.name.replace(/^Dr\.?\s+/i, '').split(' ')[0]

  useEffect(() => {
    const el = scroller.current
    if (!el) return
    const switched = lastId.current !== conversation.id
    lastId.current = conversation.id
    el.scrollTo({ top: el.scrollHeight, behavior: switched ? 'auto' : 'smooth' })
  }, [conversation.id, conversation.messages.length])

  return (
    <section
      aria-label={`Conversation with ${conversation.contact.name}`}
      className="glass flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden rounded-[22px]"
    >
      <header className="flex items-center gap-3 border-b border-white/[0.06] px-4 py-3.5 sm:px-5">
        <Button variant="ghost" size="sm" onClick={onBack} aria-label="Back to conversations" className="-ml-1 px-2 md:hidden">
          <ArrowLeft size={17} />
        </Button>
        <Avatar name={conversation.contact.name} statusClass={toneDot(meta.tone)} />
        <div className="min-w-0 flex-1 leading-tight">
          <h2 className="truncate text-[15px] font-medium text-fg">{conversation.contact.name}</h2>
          <p className="mt-0.5 truncate text-[13px] text-fg-muted">
            {conversation.contact.title} at {conversation.company}
          </p>
        </div>
        <Badge tone={meta.tone} dot className="hidden sm:inline-flex">
          {meta.label}
        </Badge>
        {onOpenInsights && (
          <Button variant="secondary" size="sm" icon={<Sparkles size={14} />} onClick={onOpenInsights}>
            <span className="hidden sm:inline">AI insights</span>
          </Button>
        )}
      </header>

      <div ref={scroller} className="min-h-0 flex-1 overflow-y-auto px-4 py-5 sm:px-6">
        <div className="mx-auto flex max-w-[760px] flex-col gap-3">
          {conversation.messages.map((m, i) => {
            const prev = conversation.messages[i - 1]
            const newDay = !prev || new Date(prev.sentAt).toDateString() !== new Date(m.sentAt).toDateString()
            const showSender = !prev || prev.sender !== m.sender || newDay
            return (
              <Fragment key={m.id}>
                {newDay && (
                  <div className="my-2 flex items-center gap-3 text-xs text-fg-subtle">
                    <span className="h-px flex-1 bg-white/[0.06]" />
                    {formatDayLabel(m.sentAt)}
                    <span className="h-px flex-1 bg-white/[0.06]" />
                  </div>
                )}
                <MessageBubble
                  message={m}
                  showSender={showSender && m.sender !== 'system'}
                  senderName={m.sender === 'outzaar' ? 'OUTZAAR' : firstName}
                  fresh={freshIds.has(m.id)}
                />
              </Fragment>
            )
          })}
        </div>
      </div>

      <div className="border-t border-white/[0.06] p-3 sm:p-4">
        <div className="mx-auto max-w-[760px]">
          <Composer
            value={draft}
            onChange={onDraft}
            onSend={onSend}
            channel={channel}
            onChannel={onChannel}
            suggestion={suggestion}
            textareaRef={textareaRef}
          />
        </div>
      </div>
    </section>
  )
}
