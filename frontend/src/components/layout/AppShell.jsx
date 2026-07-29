import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import {
  Award,
  BarChart3,
  BookOpen,
  Calendar as CalendarIcon,
  FileText,
  LayoutDashboard,
  ListTree,
  LogOut,
  Menu,
  Moon,
  Repeat,
  Rocket,
  Settings as SettingsIcon,
  Sun,
  UserRound,
  Wand2,
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

const NAV_ITEMS = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/planner', label: 'Study Planner', icon: Wand2 },
  { to: '/subjects', label: 'Subjects', icon: BookOpen },
  { to: '/syllabus', label: 'Syllabus', icon: ListTree },
  { to: '/calendar', label: 'Calendar', icon: CalendarIcon },
  { to: '/revision', label: 'Revision', icon: Repeat },
  { to: '/past-papers', label: 'Past Papers', icon: FileText },
  { to: '/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/achievements', label: 'Achievements', icon: Award },
  { to: '/profile', label: 'Profile', icon: UserRound },
  { to: '/settings', label: 'Settings', icon: SettingsIcon },
]

function Brand({ className }) {
  return (
    <div className={cn('flex items-center gap-2.5 px-1', className)}>
      <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 text-white shadow-glow">
        <Rocket className="size-4.5" />
      </span>
      <span className="font-display text-lg font-bold tracking-tight">
        StudyPilot <span className="text-gradient">AI</span>
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
              'flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-muted-foreground transition-colors',
              'hover:bg-muted hover:text-foreground',
              isActive && 'bg-primary/10 font-semibold text-primary hover:bg-primary/10 hover:text-primary',
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
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
            className="size-4.5"
          >
            <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
            <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
          </svg>
          {unread > 0 && (
            <span className="absolute right-1.5 top-1.5 size-2 rounded-full bg-rose-500 ring-2 ring-card" />
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

  useEffect(() => setMobileOpen(false), [location.pathname])

  const handleSignOut = () => {
    signOut()
    toast.info('Signed out', 'See you back soon!')
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
              onClick={() => setMobileOpen(false)}
              className="fixed inset-0 z-40 bg-slate-950/50 backdrop-blur-sm lg:hidden"
            />
            <motion.aside
              initial={{ x: '-100%' }}
              animate={{ x: 0 }}
              exit={{ x: '-100%' }}
              transition={{ type: 'spring', stiffness: 340, damping: 34 }}
              className="fixed inset-y-0 left-0 z-50 flex w-72 flex-col bg-card shadow-lift lg:hidden"
            >
              <div className="flex h-16 items-center justify-between border-b border-border/70 px-4">
                <Brand />
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setMobileOpen(false)}
                  aria-label="Close menu"
                >
                  <X className="size-5" />
                </Button>
              </div>
              <NavLinks onNavigate={() => setMobileOpen(false)} />
              <div className="border-t border-border/70 p-3">
                <button
                  onClick={handleSignOut}
                  className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                >
                  <LogOut className="size-4.5" />
                  Logout
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
