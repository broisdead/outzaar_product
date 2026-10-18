import { ArrowUp } from 'lucide-react'
import { useEffect, useRef, type KeyboardEvent } from 'react'
import { examples } from '../../data/icp'
import { cn } from '../../lib/cn'

interface IcpInputProps {
  value: string
  onChange: (value: string) => void
  onSubmit: () => void
  busy: boolean
  highlight: boolean
}

export default function IcpInput({ value, onChange, onSubmit, busy, highlight }: IcpInputProps) {
  const ref = useRef<HTMLTextAreaElement>(null)

  // Grow with content so long descriptions stay visible.
  useEffect(() => {
    const el = ref.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 220)}px`
  }, [value])

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (value.trim() && !busy) onSubmit()
    }
  }

  return (
    <div
      className={cn(
        'glass edge-light rounded-[22px] p-5 pb-4 transition-shadow duration-500 sm:p-6 sm:pb-5',
        highlight && 'shadow-[0_0_0_1px_rgba(107,111,245,0.5),0_0_60px_-10px_rgba(91,124,255,0.4)]',
      )}
    >
      <label htmlFor="icp-input" className="sr-only">
        Describe your ideal customer
      </label>
      <textarea
        id="icp-input"
        ref={ref}
        rows={2}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={onKeyDown}
        placeholder="Describe your ideal customer..."
        className="block w-full resize-none bg-transparent text-[19px] leading-[1.5] tracking-[-0.01em] text-fg placeholder:text-fg-subtle focus:outline-none sm:text-[22px]"
      />

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-fg-subtle">Try</span>
          {examples.map((ex) => (
            <button
              key={ex.label}
              type="button"
              onClick={() => onChange(ex.text)}
              className="rounded-full border border-white/[0.08] px-3 py-1 text-xs text-fg-muted transition hover:border-white/20 hover:bg-white/[0.05] hover:text-fg"
            >
              {ex.label}
            </button>
          ))}
        </div>

        <button
          type="button"
          onClick={onSubmit}
          disabled={!value.trim() || busy}
          aria-label="Update what OUTZAAR understands"
          className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-b from-brand-blue to-brand-indigo text-white shadow-[0_6px_18px_-6px_rgba(91,124,255,0.8)] transition hover:brightness-110 disabled:opacity-40"
        >
          {busy ? <span className="spinner" aria-hidden /> : <ArrowUp size={17} />}
        </button>
      </div>
    </div>
  )
}
