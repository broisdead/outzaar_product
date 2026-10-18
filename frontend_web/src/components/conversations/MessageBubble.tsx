import { motion } from 'framer-motion'
import { Check, CheckCheck, Mail, MessageCircle } from 'lucide-react'
import { cn } from '../../lib/cn'
import { formatClock } from '../../lib/time'
import type { Message } from '../../types'

interface Props {
  message: Message
  showSender: boolean
  senderName: string
  fresh: boolean
}

function Delivery({ state }: { state: Message['delivery'] }) {
  if (state === 'sending') return <span className="text-[11px] text-fg-subtle">Sending</span>
  if (state === 'sent') return <span className="text-[11px] text-fg-subtle">Sent</span>
  if (state === 'failed') return <span className="text-[11px] text-[#F87171]">Failed</span>
  if (state === 'read') return <CheckCheck size={13} className="text-[#8FA3FF]" aria-label="Read" />
  if (state === 'delivered') return <Check size={13} className="text-fg-subtle" aria-label="Delivered" />
  
  return null
}

export default function MessageBubble({ message, showSender, senderName, fresh }: Props) {
  const motionProps = fresh
    ? { initial: { opacity: 0, y: 8 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.22 } }
    : {}

  if (message.sender === 'system') {
    return (
      <motion.div {...motionProps} className="flex justify-center py-1">
        <span className="rounded-full border border-ok/20 bg-ok/[0.07] px-3.5 py-1.5 text-xs text-ok">
          {message.body}
        </span>
      </motion.div>
    )
  }

  const mine = message.sender === 'outzaar'
  const ChannelIcon = message.channel === 'email' ? Mail : MessageCircle

  return (
    <motion.div {...motionProps} className={cn('flex flex-col', mine ? 'items-end' : 'items-start')}>
      {showSender && (
        <span className={cn('mb-1.5 px-1 text-xs font-medium', mine ? 'text-[#9DB0FF]' : 'text-fg-muted')}>
          {senderName}
        </span>
      )}
      <div
        className={cn(
          'max-w-[88%] rounded-2xl px-4 py-3 text-[14.5px] leading-relaxed sm:max-w-[76%]',
          mine
            ? 'rounded-br-md border border-brand-blue/30 bg-gradient-to-br from-brand-blue/[0.26] to-brand-violet/[0.2] text-fg'
            : 'glass rounded-bl-md text-fg',
        )}
      >
        <p className="whitespace-pre-wrap">{message.body}</p>
      </div>
      <div className="mt-1.5 flex items-center gap-1.5 px-1 text-[11px] text-fg-subtle">
        <ChannelIcon size={11} />
        <span className="tabular-nums">{formatClock(message.sentAt)}</span>
        {mine && <Delivery state={message.delivery} />}
      </div>
    </motion.div>
  )
}
