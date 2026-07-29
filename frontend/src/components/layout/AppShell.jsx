import { useCallback, useEffect, useRef, useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import {
  BarChart3,
  Bell,
  BookOpen,
  CalendarClock,
  CalendarDays,
  ClipboardList,
  GraduationCap,
  LayoutDashboard,
  ListTree,
  LogOut,
  Menu,
  Moon,
  RotateCcw,
  Settings as SettingsIcon,
  Sun,
  Trophy,
  UserRound,
  X,
} from 'lucide-react'

import { useAuth } from '@/context/AuthContext'
import { StudySessionProvider } from '@/context/StudySessionContext'
import { useTheme } from '@/context/ThemeContext'
import { useToast } from '@/context/ToastContext'
import api from '@/lib/api'
import { cn } from '@/lib/utils'
import { SessionReminderDialog } from '@/components/session/SessionReminderDialog'
import { SessionTimer } from '@/components/session/SessionTimer'
import { UserAvatar } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

/*
 * Icons name the thing they lead to. The previous set had a rocket for a
 * revision app and a magic wand for the timetable, both of which say "generated
 * template" rather than "study tool".
 */
const NAV_ITEMS = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  // A timetable with times on it, not a magic trick.
  { to: '/planner', label: 'Study Planner', icon: CalendarClock },
  { to: '/subjects', label: 'Subjects', icon: BookOpen },
  { to: '/syllabus', label: 'Syllabus', icon: ListTree },
  { to: '/calendar', label: 'Calendar', icon: CalendarDays },
  // Spaced repetition: coming back round to something.
  { to: '/revision', label: 'Revision', icon: RotateCcw },
  { to: '/past-papers', label: 'Past Papers', icon: ClipboardList },
  { to: '/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/achievements', label: 'Achievements', icon: Trophy },
  { to: '/profile', label: 'Profile', icon: UserRound },
  { to: '/settings', label: 'Settings', icon: SettingsIcon },
]

function Brand({ className }) {
  return (
    <div className={cn('flex items-center gap-2.5 px-1', className)}>
      <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-primary text-primary-foreground">
        <GraduationCap className="size-5" />
      </span>
      <span className="font-display text-lg font-bold tracking-tight">
        StudyPilot <span className="text-primary">AI</span>
      </span>
    </div>
  )
}

function NavLinks({ onNavigate }) {
  return (
    <nav className="flex flex-1 flex-col gap-1 overflow-y-auto px-2 py-2">
      {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          onClick={onNavigate}
          className={({ isActive }) =>
            cn(
              // min-h-11 keeps every row a comfortable 44px tap target.
              'flex min-h-11 items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium text-muted-foreground transition-colors',
              'hover:bg-muted hover:text-foreground',
              isActive &&
                'bg-primary/10 font-semibold text-primary hover:bg-primary/10 hover:text-primary',
            )
          }
        >
          <Icon className="size-4.5 shrink-0" />
          {label}
        </NavLink>
      ))}
    </nav>
  )
}

function ThemeToggle() {
  const { isDark, toggleTheme } = useTheme()
  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={toggleTheme}
      aria-label="Toggle dark mode"
      title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
    >
      {isDark ? <Sun className="size-4.5" /> : <Moon className="size-4.5" />}
    </Button>
  )
}

function NotificationsBell() {
  const [items, setItems] = useState([])
  const [loaded, setLoaded] = useState(false)

  const load = async () => {
    try {
      const data = await api.notifications.list({ limit: 8 })
      setItems(data || [])
    } catch {
      /* silent — the bell just stays empty */
    } finally {
      setLoaded(true)
    }
  }

  useEffect(() => {
    load()
    const interval = setInterval(load, 60_000)
    return () => clearInterval(interval)
  }, [])

  const unread = items.filter((n) => !n.is_read).length

  return (
    <DropdownMenu onOpenChange={(open) => open && !loaded && load()}>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="relative" aria-label="Notifications">
          <Bell className="size-4.5" />
          {unread > 0 && (
            <span className="absolute right-2 top-2 size-2 rounded-full bg-accent ring-2 ring-background" />
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80">
        <div className="flex items-center justify-between px-2.5 py-1.5">
          <DropdownMenuLabel className="p-0">Notifications</DropdownMenuLabel>
          {unread > 0 && (
            <button
              className="text-xs font-semibold text-primary hover:underline"
              onClick={async () => {
                await api.notifications.markAllRead()
                load()
              }}
            >
              Mark all read
            </button>
          )}
        </div>
        <DropdownMenuSeparator />
        {items.length === 0 ? (
          <p className="px-2.5 py-6 text-center text-sm text-muted-foreground">
            You're all caught up.
          </p>
        ) : (
          <div className="max-h-80 space-y-0.5 overflow-y-auto">
            {items.map((note) => (
              <DropdownMenuItem
                key={note.id}
                className="flex-col items-start gap-0.5"
                onSelect={() => !note.is_read && api.notifications.markRead(note.id)}
              >
                <span className={cn('text-sm', !note.is_read && 'font-semibold')}>
                  {note.title}
                </span>
                <span className="line-clamp-2 text-xs text-muted-foreground">
                  {note.message}
                </span>
              </DropdownMenuItem>
            ))}
          </div>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

function AppShellLayout() {
  const { user, signOut } = useAuth()
  const { toast } = useToast()
  const navigate = useNavigate()
  const location = useLocation()
  const [mobileOpen, setMobileOpen] = useState(false)
  const drawerRef = useRef(null)
  const closeDrawer = useCallback(() => setMobileOpen(false), [])

  useEffect(() => setMobileOpen(false), [location.pathname])

  // Escape closes the drawer, and while it is open the page behind must not
  // scroll: on a phone, scrolling the body under an open drawer is what makes
  // it feel like you are stuck in it.
  useEffect(() => {
    if (!mobileOpen) return undefined

    const onKeyDown = (event) => {
      if (event.key === 'Escape') closeDrawer()
    }
    window.addEventListener('keydown', onKeyDown)

    const { overflow, touchAction } = document.body.style
    document.body.style.overflow = 'hidden'
    document.body.style.touchAction = 'none'

    // Move focus into the drawer so the next Tab lands on its links rather
    // than continuing down the page behind it.
    drawerRef.current?.focus()

    return () => {
      window.removeEventListener('keydown', onKeyDown)
      document.body.style.overflow = overflow
      document.body.style.touchAction = touchAction
    }
  }, [mobileOpen, closeDrawer])

  // Keep the tab ring inside the drawer while it is open.
  const onDrawerKeyDown = (event) => {
    if (event.key !== 'Tab') return
    const focusable = drawerRef.current?.querySelectorAll(
      'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])',
    )
    if (!focusable?.length) return
    const first = focusable[0]
    const last = focusable[focusable.length - 1]
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault()
      last.focus()
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault()
      first.focus()
    }
  }

  const handleSignOut = () => {
    signOut()
    toast.info('Signed out', 'See you back soon')
    navigate('/', { replace: true })
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col border-r border-border/70 bg-card/60 backdrop-blur-xl lg:flex">
        <div className="flex h-16 items-center border-b border-border/70 px-4">
          <Brand />
        </div>
        <NavLinks />
        <div className="border-t border-border/70 p-3">
          <button
            onClick={handleSignOut}
            className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive"
          >
            <LogOut className="size-4.5" />
            Logout
          </button>
        </div>
      </aside>

      {/* Mobile drawer */}
      <AnimatePresence>
        {mobileOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={closeDrawer}
              // Labelled and clickable: tapping anywhere outside the drawer is
              // the gesture most people try first.
              role="button"
              tabIndex={-1}
              aria-label="Close menu"
              className="fixed inset-0 z-40 bg-slate-950/60 backdrop-blur-sm lg:hidden"
            />
            <motion.aside
              ref={drawerRef}
              tabIndex={-1}
              role="dialog"
              aria-modal="true"
              aria-label="Main menu"
              onKeyDown={onDrawerKeyDown}
              initial={{ x: '-100%' }}
              animate={{ x: 0 }}
              exit={{ x: '-100%' }}
              transition={{ type: 'spring', stiffness: 340, damping: 34 }}
              className="fixed inset-y-0 left-0 z-50 flex w-[min(19rem,85vw)] flex-col bg-card shadow-lift outline-none lg:hidden"
            >
              <div className="flex h-16 shrink-0 items-center justify-between gap-2 border-b border-border/70 px-3">
                <Brand />
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={closeDrawer}
                  aria-label="Close menu"
                  className="shrink-0"
                >
                  <X className="size-5" />
                </Button>
              </div>
              <NavLinks onNavigate={closeDrawer} />
              <div className="shrink-0 border-t border-border/70 p-3">
                <button
                  onClick={handleSignOut}
                  className="flex min-h-11 w-full items-center gap-3 rounded-xl px-3 text-sm font-medium text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                >
                  <LogOut className="size-4.5" />
                  Log out
                </button>
              </div>
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      <div className="lg:pl-64">
        <header className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-border/70 bg-background/80 px-4 backdrop-blur-xl sm:px-6">
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden"
            onClick={() => setMobileOpen(true)}
            aria-label="Open menu"
          >
            <Menu className="size-5" />
          </Button>

          <div className="flex-1" />

          <div className="flex items-center gap-1.5">
            <ThemeToggle />
            <NotificationsBell />
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button className="ml-1 flex items-center gap-2 rounded-full pr-1 transition-colors hover:bg-muted">
                  <UserAvatar user={user} className="size-8" />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuLabel className="flex flex-col gap-0.5">
                  <span className="text-sm font-semibold text-foreground">{user?.name}</span>
                  <span className="truncate text-xs font-normal text-muted-foreground">
                    {user?.email}
                  </span>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onSelect={() => navigate('/profile')}>
                  <UserRound /> Profile
                </DropdownMenuItem>
                <DropdownMenuItem onSelect={() => navigate('/settings')}>
                  <SettingsIcon /> Settings
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem destructive onSelect={handleSignOut}>
                  <LogOut /> Logout
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>

        <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8">
          <Outlet />
        </main>
      </div>

      {/* Session reminders, the running timer and the end-of-session alarm. */}
      <SessionReminderDialog />
      <SessionTimer />
    </div>
  )
}

export function AppShell() {
  return (
    <StudySessionProvider>
      <AppShellLayout />
    </StudySessionProvider>
  )
}

export default AppShell
