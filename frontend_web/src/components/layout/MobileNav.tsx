import { NavLink } from 'react-router-dom'
import { cn } from '../../lib/cn'
import { navItems } from './navItems'

export default function MobileNav() {
  return (
    <nav
      aria-label="Main"
      className="z-30 flex shrink-0 border-t border-white/[0.07] bg-ink-900/90 px-2 pb-[env(safe-area-inset-bottom)] backdrop-blur-xl lg:hidden"
    >
      {navItems.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          className={({ isActive }) =>
            cn(
              'flex flex-1 flex-col items-center gap-1 py-2.5 text-[11px] font-medium transition-colors',
              isActive ? 'text-[#9DB0FF]' : 'text-fg-subtle',
            )
          }
        >
          <Icon size={19} strokeWidth={1.75} />
          {label}
        </NavLink>
      ))}
    </nav>
  )
}
