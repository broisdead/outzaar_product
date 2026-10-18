import { Check } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { cn } from '../../lib/cn'
import { nextWeekWeekday } from '../../lib/time'
import type { Channel } from '../../types'
import Button from '../ui/Button'
import Dialog from '../ui/Dialog'

interface Props {
  open: boolean
  contactName: string
  channel: Channel
  onClose: () => void
  onConfirm: (slotLabel: string) => Promise<void>
}

export default function BookMeetingDialog({ open, contactName, channel, onClose, onConfirm }: Props) {
  const slots = useMemo(() => {
    const tue = nextWeekWeekday(2)
    const wed = nextWeekWeekday(3)
    const day = (d: Date) => d.toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'short' })
    return [
      { id: 's1', day: day(tue), time: '11:00 AM' },
      { id: 's2', day: day(tue), time: '3:30 PM' },
      { id: 's3', day: day(wed), time: '10:30 AM' },
      { id: 's4', day: day(wed), time: '4:00 PM' },
    ]
  }, [])

  const [selected, setSelected] = useState(slots[0].id)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (open) {
      setSelected(slots[0].id)
      setBusy(false)
    }
  }, [open, slots])

  const confirm = async () => {
    const slot = slots.find((s) => s.id === selected)!
    setBusy(true)
    await onConfirm(`${slot.day}, ${slot.time} IST`)
  }

  return (
    <Dialog open={open} onClose={onClose} label="Book a meeting">
      <h2 className="text-lg font-semibold tracking-[-0.01em] text-fg">Book a meeting</h2>
      <p className="mt-1.5 text-sm text-fg-muted">
        Offer {contactName.split(' ')[0]} a 20-minute call. The invite goes out by{' '}
        {channel === 'email' ? 'email' : 'WhatsApp'}.
      </p>

      <div role="radiogroup" aria-label="Meeting time" className="mt-5 space-y-2">
        {slots.map((s) => {
          const active = s.id === selected
          return (
            <button
              key={s.id}
              type="button"
              role="radio"
              aria-checked={active}
              onClick={() => setSelected(s.id)}
              className={cn(
                'flex w-full items-center justify-between rounded-xl border px-4 py-3 text-left transition-colors',
                active
                  ? 'border-brand-indigo/60 bg-brand-blue/[0.1]'
                  : 'border-white/[0.08] bg-white/[0.02] hover:border-white/[0.16]',
              )}
            >
              <span>
                <span className="block text-sm font-medium text-fg">{s.day}</span>
                <span className="block text-[13px] text-fg-muted">{s.time} IST</span>
              </span>
              {active && <Check size={16} className="text-[#9DB0FF]" />}
            </button>
          )
        })}
      </div>

      <div className="mt-6 flex justify-end gap-2.5">
        <Button variant="ghost" onClick={onClose} disabled={busy}>
          Cancel
        </Button>
        <Button variant="primary" onClick={confirm} loading={busy}>
          Send invite
        </Button>
      </div>
    </Dialog>
  )
}
