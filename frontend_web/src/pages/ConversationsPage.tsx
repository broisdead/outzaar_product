import { useCallback, useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import AIPanel from '../components/conversations/AIPanel'
import BookMeetingDialog from '../components/conversations/BookMeetingDialog'
import ChatThread from '../components/conversations/ChatThread'
import ConversationList from '../components/conversations/ConversationList'
import Drawer from '../components/ui/Drawer'
import Skeleton from '../components/ui/Skeleton'
import { useMediaQuery } from '../hooks/useMediaQuery'
import { cn } from '../lib/cn'
import { analyzeConversation, bookMeeting, getConversations, sendMessage } from '../services/api'
import type { AIAnalysis, Channel, Conversation, Message } from '../types'

export default function ConversationsPage() {
  const [params, setParams] = useSearchParams()
  const [conversations, setConversations] = useState<Conversation[] | null>(null)
  const [analyses, setAnalyses] = useState<Record<string, AIAnalysis>>({})
  const [drafts, setDrafts] = useState<Record<string, string>>({})
  const [channels, setChannels] = useState<Record<string, Channel>>({})
  const [handled, setHandled] = useState<Set<string>>(new Set())
  const [freshIds, setFreshIds] = useState<Set<string>>(new Set())
  const [pane, setPane] = useState<'list' | 'chat'>(params.get('c') ? 'chat' : 'list')
  const [insightsOpen, setInsightsOpen] = useState(false)
  const [bookingOpen, setBookingOpen] = useState(false)

  const isWide = useMediaQuery('(min-width: 1280px)')
  const composerRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    let cancelled = false
    getConversations().then((data) => {
      if (!cancelled) setConversations(data)
    })
    return () => {
      cancelled = true
    }
  }, [])

  const requested = params.get('c')
  const selectedId =
    conversations && conversations.some((c) => c.id === requested)
      ? requested
      : (conversations?.[0]?.id ?? null)
  const selected = conversations?.find((c) => c.id === selectedId) ?? null

  // Fetch the AI read of the selected conversation once, then cache it.
  useEffect(() => {
    if (!selectedId || analyses[selectedId]) return
    let cancelled = false
    analyzeConversation(selectedId).then((a) => {
      if (!cancelled) setAnalyses((prev) => ({ ...prev, [selectedId]: a }))
    })
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId])

  // Opening a conversation marks it as read.
  useEffect(() => {
    if (!selectedId) return
    setConversations((prev) => {
      if (!prev || !prev.some((c) => c.id === selectedId && c.unread)) return prev
      return prev.map((c) => (c.id === selectedId ? { ...c, unread: false } : c))
    })
  }, [selectedId, conversations === null])

  const patch = useCallback((id: string, fn: (c: Conversation) => Conversation) => {
    setConversations((prev) => prev && prev.map((c) => (c.id === id ? fn(c) : c)))
  }, [])

  const select = (id: string) => {
    setParams({ c: id }, { replace: true })
    setPane('chat')
  }

  const setDraft = (id: string, value: string) => setDrafts((d) => ({ ...d, [id]: value }))

  const focusComposer = () => window.setTimeout(() => composerRef.current?.focus(), 60)

  const applyResponse = (text: string) => {
    if (!selected) return
    setDraft(selected.id, text)
    setInsightsOpen(false)
    focusComposer()
  }

  const handleSend = async () => {
    if (!selected) return
    const id = selected.id
    const body = (drafts[id] ?? '').trim()
    if (!body) return
    const channel = channels[id] ?? selected.channel
    const tempId = `local-${Date.now()}`
    const optimistic: Message = {
      id: tempId,
      sender: 'outzaar',
      body,
      channel,
      sentAt: new Date().toISOString(),
      delivery: 'sending',
    }

    setFreshIds((s) => new Set(s).add(tempId))
    setDraft(id, '')
    setHandled((s) => new Set(s).add(id))
    patch(id, (c) => ({
      ...c,
      messages: [...c.messages, optimistic],
      status: c.status === 'followup' || c.status === 'awaiting' ? 'awaiting' : c.status,
    }))

    const sent = await sendMessage(id, body, channel)
    // Keep the temporary id so the bubble does not remount.
    patch(id, (c) => ({
      ...c,
      messages: c.messages.map((m) => (m.id === tempId ? { ...sent, id: tempId } : m)),
    }))
  }

  const handleBook = async (slotLabel: string) => {
    if (!selected) return
    const id = selected.id
    const channel = channels[id] ?? selected.channel
    const note = await bookMeeting(id, slotLabel, channel)
    setFreshIds((s) => new Set(s).add(note.id))
    setHandled((s) => new Set(s).add(id))
    patch(id, (c) => ({ ...c, status: 'meeting', messages: [...c.messages, note] }))
    setBookingOpen(false)
  }

  const analysis = selected ? (analyses[selected.id] ?? null) : null

  const panel = selected && (
    <AIPanel
      key={selected.id}
      conversation={selected}
      analysis={analysis}
      handled={handled.has(selected.id)}
      onUse={applyResponse}
      onBook={() => setBookingOpen(true)}
      bare={!isWide}
      className={isWide ? 'hidden w-[340px] shrink-0 xl:block' : 'block min-h-0 flex-1'}
    />
  )

  return (
    <div className="flex min-h-0 flex-1 gap-3 p-3 sm:gap-4 sm:p-4 lg:p-5">
      <ConversationList
        conversations={conversations}
        selectedId={selectedId}
        onSelect={select}
        className={cn('w-full shrink-0 md:w-[300px] lg:w-[330px]', pane === 'list' ? 'flex' : 'hidden md:flex')}
      />

      <div className={cn('min-h-0 min-w-0 flex-1 flex-col', pane === 'chat' ? 'flex' : 'hidden md:flex')}>
        {selected ? (
          <ChatThread
            conversation={selected}
            channel={channels[selected.id] ?? selected.channel}
            onChannel={(c) => setChannels((prev) => ({ ...prev, [selected.id]: c }))}
            draft={drafts[selected.id] ?? ''}
            onDraft={(v) => setDraft(selected.id, v)}
            onSend={handleSend}
            suggestion={analysis?.suggestedResponse}
            textareaRef={composerRef}
            onBack={() => setPane('list')}
            onOpenInsights={isWide ? undefined : () => setInsightsOpen(true)}
            freshIds={freshIds}
          />
        ) : (
          <div className="glass flex-1 rounded-[22px] p-6" aria-busy>
            <div className="flex items-center gap-3">
              <Skeleton className="h-10 w-10 rounded-full" />
              <div className="space-y-2">
                <Skeleton className="h-3.5 w-40" />
                <Skeleton className="h-3 w-56" />
              </div>
            </div>
            <div className="mt-10 space-y-5">
              <Skeleton className="h-16 w-2/3" />
              <Skeleton className="ml-auto h-14 w-1/2" />
              <Skeleton className="h-12 w-3/5" />
            </div>
          </div>
        )}
      </div>

      {isWide && panel}

      {!isWide && (
        <Drawer open={insightsOpen} onClose={() => setInsightsOpen(false)} label="OUTZAAR AI analysis" width={400}>
          {panel}
        </Drawer>
      )}

      <BookMeetingDialog
        open={bookingOpen}
        contactName={selected?.contact.name ?? ''}
        channel={selected ? (channels[selected.id] ?? selected.channel) : 'email'}
        onClose={() => setBookingOpen(false)}
        onConfirm={handleBook}
      />
    </div>
  )
}
