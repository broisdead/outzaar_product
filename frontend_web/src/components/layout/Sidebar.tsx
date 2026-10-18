import { motion } from 'framer-motion'
import { NavLink } from 'react-router-dom'
import { cn } from '../../lib/cn'
import Logo from '../ui/Logo'
import AgentStatus from './AgentStatus'
import { navItems } from './navItems'

export default function Sidebar() {
  return (
    <aside className="hidden w-[248px] shrink-0 flex-col border-r border-white/[0.06] bg-ink-900/60 px-4 pb-4 pt-6 backdrop-blur-xl lg:flex">
      <div className="px-2">
        <Logo />
      </div>

      <nav className="mt-9 flex flex-col gap-1" aria-label="Main">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink key={to} to={to} className="relative rounded-xl outline-offset-0">
            {({ isActive }) => (
              <span
                className={cn(
                  'relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-[14px] font-medium transition-colors',
                  isActive ? 'text-fg' : 'text-fg-muted hover:text-fg',
                )}
              >
                {isActive && (
                  <motion.span
                    layoutId="nav-active"
                    className="absolute inset-0 rounded-xl border border-white/[0.09] bg-gradient-to-r from-brand-blue/[0.16] to-brand-violet/[0.06]"
                    transition={{ type: 'spring', stiffness: 500, damping: 40 }}
                  />
                )}
                <Icon size={18} strokeWidth={1.75} className={cn('relative', isActive && 'text-[#9DB0FF]')} />
                <span className="relative">{label}</span>
              </span>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="mt-auto">
        <AgentStatus />
      </div>
    </aside>
  )
}
