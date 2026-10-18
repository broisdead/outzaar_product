import { MotionConfig, motion } from 'framer-motion'
import { Outlet, useLocation } from 'react-router-dom'
import MobileHeader from './MobileHeader'
import MobileNav from './MobileNav'
import Sidebar from './Sidebar'

// Soft colour behind everything. Fixed, so it does not scroll with content.
function Ambient() {
  return (
    <div
      aria-hidden
      className="pointer-events-none fixed inset-0 z-0"
      style={{
        background:
          'radial-gradient(900px 520px at 8% -8%, rgba(91,124,255,0.16), transparent 62%), radial-gradient(760px 480px at 96% 4%, rgba(139,108,246,0.12), transparent 60%), radial-gradient(900px 600px at 50% 118%, rgba(91,124,255,0.07), transparent 65%)',
      }}
    />
  )
}

export default function AppShell() {
  const { pathname } = useLocation()

  return (
    <MotionConfig reducedMotion="user">
      <div className="relative flex h-dvh flex-col overflow-hidden bg-ink-950 lg:flex-row">
        <Ambient />
        <MobileHeader />
        <div className="relative z-10 hidden lg:flex">
          <Sidebar />
        </div>
        <main className="relative z-10 flex min-h-0 min-w-0 flex-1 flex-col overflow-y-auto">
          <motion.div
            key={pathname}
            className="flex min-h-0 flex-1 flex-col"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.22 }}
          >
            <Outlet />
          </motion.div>
        </main>
        <MobileNav />
      </div>
    </MotionConfig>
  )
}
