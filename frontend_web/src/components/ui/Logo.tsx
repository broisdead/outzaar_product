export function LogoMark({ size = 30 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden>
      <defs>
        <linearGradient id="oz-mark" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#5B7CFF" />
          <stop offset="1" stopColor="#8B6CF6" />
        </linearGradient>
      </defs>
      <rect width="32" height="32" rx="9" fill="#0C111D" stroke="rgba(255,255,255,0.09)" />
      <circle cx="16" cy="16" r="7" fill="none" stroke="url(#oz-mark)" strokeWidth="3.2" />
      <circle cx="22.5" cy="9.5" r="2.2" fill="#3DD6A0" />
    </svg>
  )
}

export default function Logo() {
  return (
    <div className="flex items-center gap-2.5">
      <LogoMark />
      <span className="text-[17px] font-semibold tracking-[0.01em] text-fg">OUTZAAR</span>
    </div>
  )
}
