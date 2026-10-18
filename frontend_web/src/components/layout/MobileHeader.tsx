import Logo from '../ui/Logo'

export default function MobileHeader() {
  return (
    <header className="flex shrink-0 items-center justify-between border-b border-white/[0.06] bg-ink-900/70 px-4 py-3 backdrop-blur-xl lg:hidden">
      <Logo />
      <span className="flex items-center gap-2 text-xs text-fg-muted">
        <span className="h-1.5 w-1.5 rounded-full bg-ok" />
        AI online
      </span>
    </header>
  )
}
