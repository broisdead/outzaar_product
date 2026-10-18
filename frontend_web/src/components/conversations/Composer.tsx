import { Mail, MessageCircle, Send, Sparkles } from 'lucide-react'
import { useEffect, type KeyboardEvent, type RefObject } from 'react'
import type { Channel } from '../../types'
import Button from '../ui/Button'
import Segmented from '../ui/Segmented'

interface Props {
  value: string
  onChange: (v: string) => void
  onSend: () => void
  channel: Channel
  onChannel: (c: Channel) => void
  suggestion?: string
  textareaRef: RefObject<HTMLTextAreaElement>
}

export default function Composer({
  value,
  onChange,
  onSend,
  channel,
  onChannel,
  suggestion,
  textareaRef,
}: Props) {
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`
  }, [value, textareaRef])

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (value.trim()) onSend()
    }
  }

  return (
    <div className="glass rounded-2xl p-3 focus-within:border-brand-indigo/50">
      <label htmlFor="composer" className="sr-only">
        Message
      </label>
      <textarea
        id="composer"
        ref={textareaRef}
        rows={1}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={onKeyDown}
        placeholder="Type a message..."
        className="block max-h-40 w-full resize-none bg-transparent px-2 py-1.5 text-[14.5px] leading-relaxed text-fg placeholder:text-fg-subtle focus:outline-none"
      />
      <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2.5">
          <Segmented<Channel>
            id="composer-channel"
            ariaLabel="Send channel"
            size="sm"
            value={channel}
            onChange={onChannel}
            options={[
              { value: 'email', label: 'Email', icon: <Mail size={13} /> },
              { value: 'whatsapp', label: 'WhatsApp', icon: <MessageCircle size={13} /> },
            ]}
          />
          {suggestion && (
            <Button
              variant="ghost"
              size="sm"
              icon={<Sparkles size={14} />}
              onClick={() => onChange(suggestion)}
              className="hidden sm:inline-flex"
            >
              Draft with OUTZAAR
            </Button>
          )}
        </div>
        <div className="flex items-center gap-3">
          <span className="hidden text-xs text-fg-subtle md:inline">
            Sending via {channel === 'email' ? 'Email' : 'WhatsApp'}
          </span>
          <Button
            variant="primary"
            size="sm"
            icon={<Send size={14} />}
            onClick={onSend}
            disabled={!value.trim()}
          >
            Send
          </Button>
        </div>
      </div>
    </div>
  )
}
