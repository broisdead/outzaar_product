export default function AgentStatus() {
  return (
    <div className="rounded-xl border border-white/[0.07] bg-white/[0.03] p-3.5">
      <div className="flex items-center gap-2.5">
        <span className="relative flex h-2 w-2">
          <span className="absolute inset-0 rounded-full bg-ok animate-beacon motion-reduce:animate-none" />
          <span className="relative h-2 w-2 rounded-full bg-ok" />
        </span>
        <span className="text-[13px] font-medium text-fg">OUTZAAR AI is online</span>
      </div>
      <p className="mt-1.5 pl-[18px] text-xs leading-relaxed text-fg-subtle">
        Monitoring 5 conversations and 248 prospects.
      </p>
    </div>
  )
}
