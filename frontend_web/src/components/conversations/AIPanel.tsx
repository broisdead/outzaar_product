import { motion } from 'framer-motion'
import { Calendar, Check, Minus, Pencil, Target, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { statusMeta } from '../../data/conversations'
import { cn } from '../../lib/cn'
import type { AIAnalysis, Conversation, SignalTone } from '../../types'
import Badge from '../ui/Badge'
import Button from '../ui/Button'
import { LogoMark } from '../ui/Logo'
import Skeleton from '../ui/Skeleton'

interface Props {
  conversation: Conversation
  analysis: AIAnalysis | null
  handled: boolean
  onUse: (text: string) => void
  onBook: () => void
  className?: string
  /** Render without the glass card chrome (used inside a drawer). */
  bare?: boolean
}

const barColor = { green: '#3DD6A0', blue: '#6B8BFF', amber: '#F2B84B', red: '#F0708A', slate: '#8791A8', violet: '#8B6CF6' }

function SignalIcon({ tone }: { tone: SignalTone }) {
  if (tone === 'positive')
    return (
      <span className="flex h-[18px] w-[18px] items-center justify-center rounded-full bg-ok/15 text-ok">
        <Check size={11} strokeWidth={3} />
      </span>
    )
  if (tone === 'negative')
    return (
      <span className="flex h-[18px] w-[18px] items-center justify-center rounded-full bg-bad/15 text-bad">
        <X size={11} strokeWidth={3} />
      </span>
    )
  return (
    <span className="flex h-[18px] w-[18px] items-center justify-center rounded-full bg-white/[0.08] text-fg-muted">
      <Minus size={11} strokeWidth={3} />
    </span>
  )
}

export default function AIPanel({ conversation, analysis, handled, onUse, onBook, className, bare }: Props) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState('')

  useEffect(() => {
    setDraft(analysis?.suggestedResponse ?? '')
    setEditing(false)
  }, [analysis, conversation.id])

  const meta = statusMeta[conversation.status]
  const canBook = analysis ? analysis.actionKind !== 'close' : false

  return (
    <aside
      aria-label="OUTZAAR AI analysis"
      className={cn('min-h-0 overflow-y-auto', !bare && 'glass rounded-[22px]', className)}
    >
      <div className={cn('flex items-center gap-3 px-5 pb-4 pt-5', bare && 'pr-11')}>
        <LogoMark size={30} />
        <div className="leading-tight">
          <h2 className="text-[15px] font-medium text-fg">OUTZAAR AI</h2>
          <p className="mt-0.5 text-xs text-fg-muted">Understanding this conversation</p>
        </div>
      </div>

      {!analysis ? (
        <div className="space-y-6 px-5 pb-6 pt-2" aria-busy aria-label="Analyzing conversation">
          <div className="flex gap-6">
            <Skeleton className="h-10 w-32" />
            <Skeleton className="h-10 w-24" />
          </div>
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
      ) : (
        <motion.div
          key={conversation.id}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.25 }}
          className="space-y-6 px-5 pb-6"
        >
          <div className="grid grid-cols-2 gap-4 border-y border-white/[0.06] py-4">
            <div>
              <p className="text-xs text-fg-subtle">Intent</p>
              <div className="mt-2">
                <Badge tone={meta.tone} dot>
                  {analysis.intent}
                </Badge>
              </div>
            </div>
            <div>
              <p className="text-xs text-fg-subtle">Confidence</p>
              <p className="mt-1 text-xl font-semibold tabular-nums leading-none text-fg">
                {analysis.confidence}%
              </p>
              <div className="mt-2 h-1 overflow-hidden rounded-full bg-white/[0.08]">
                <motion.div
                  className="h-full rounded-full"
                  style={{ background: barColor[meta.tone] }}
                  initial={{ width: 0 }}
                  animate={{ width: `${analysis.confidence}%` }}
                  transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
                />
              </div>
            </div>
          </div>

          <section>
            <h3 className="text-[13px] font-medium text-fg">AI summary</h3>
            <p className="mt-2 text-sm leading-relaxed text-fg-muted">{analysis.summary}</p>
          </section>

          <section>
            <h3 className="text-[13px] font-medium text-fg">Recommended action</h3>
            <div className="mt-2 flex items-center gap-3 rounded-xl border border-white/[0.08] bg-white/[0.03] px-3.5 py-3">
              <Target size={16} className="shrink-0 text-[#9DB0FF]" />
              <span className="text-sm text-fg">{analysis.recommendedAction}</span>
            </div>
          </section>

          {handled ? (
            <section className="rounded-xl border border-ok/20 bg-ok/[0.06] px-4 py-3.5">
              <p className="text-sm font-medium text-ok">Response sent</p>
              <p className="mt-1 text-[13px] leading-relaxed text-fg-muted">
                OUTZAAR is watching for {conversation.contact.name.split(' ')[0]}'s next reply and will update this analysis.
              </p>
            </section>
          ) : (
            <section>
              <h3 className="text-[13px] font-medium text-fg">Suggested response</h3>
              {editing ? (
                <textarea
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  rows={6}
                  aria-label="Edit suggested response"
                  className="field mt-2 w-full resize-none rounded-xl px-3.5 py-3 text-sm leading-relaxed"
                />
              ) : (
                <div className="mt-2 rounded-xl border-l-2 border-brand-indigo/70 bg-white/[0.03] py-3 pl-4 pr-3.5">
                  <p className="whitespace-pre-wrap text-sm leading-relaxed text-fg">{draft}</p>
                </div>
              )}
              <div className="mt-3 grid grid-cols-2 gap-2">
                <Button variant="primary" size="sm" onClick={() => onUse(draft)} disabled={!draft.trim()}>
                  Use Response
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  icon={<Pencil size={13} />}
                  onClick={() => setEditing((v) => !v)}
                >
                  {editing ? 'Done' : 'Edit Response'}
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  icon={<Calendar size={14} />}
                  onClick={onBook}
                  disabled={!canBook}
                  className="col-span-2"
                >
                  Book Meeting
                </Button>
              </div>
            </section>
          )}

          <section>
            <h3 className="text-[13px] font-medium text-fg">Conversation signals</h3>
            <ul className="mt-3 space-y-2.5">
              {analysis.signals.map((s) => (
                <li key={s.label} className="flex items-center gap-3 text-sm text-fg-muted">
                  <SignalIcon tone={s.tone} />
                  {s.label}
                </li>
              ))}
            </ul>
          </section>

          <section className="border-t border-white/[0.06] pt-5">
            <h3 className="text-[13px] font-medium text-fg">About the account</h3>
            <p className="mt-2 text-[13px] leading-relaxed text-fg-subtle">{conversation.context}</p>
          </section>
        </motion.div>
      )}
    </aside>
  )
}
