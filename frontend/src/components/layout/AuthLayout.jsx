import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowLeft, Moon, Rocket, Sun } from 'lucide-react'

import { useTheme } from '@/context/ThemeContext'
import { Button } from '@/components/ui/button'

function ThemeToggleFloating() {
  const { isDark, toggleTheme } = useTheme()
  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={toggleTheme}
      aria-label="Toggle dark mode"
      className="absolute right-4 top-4 sm:right-6 sm:top-6"
    >
      {isDark ? <Sun className="size-4.5" /> : <Moon className="size-4.5" />}
    </Button>
  )
}

/** Centred card shell shared by every authentication screen. */
export function AuthLayout({ title, subtitle, children, footer, wide = false }) {
  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-background px-4 py-12">
      <div className="pastel-mesh pointer-events-none absolute inset-0 -z-10" aria-hidden="true" />
      <ThemeToggleFloating />

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
        className={wide ? 'w-full max-w-2xl' : 'w-full max-w-md'}
      >
        <Link
          to="/"
          className="mb-6 inline-flex items-center gap-1.5 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="size-4" />
          Back to home
        </Link>

        <div className="rounded-3xl border border-border/70 bg-card/95 p-7 shadow-lift backdrop-blur sm:p-9">
          <div className="mb-7 flex flex-col items-center text-center">
            <span className="mb-4 grid size-12 place-items-center rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-600 text-white shadow-glow">
              <Rocket className="size-5.5" />
            </span>
            <h1 className="font-display text-2xl font-bold tracking-tight">{title}</h1>
            {subtitle && <p className="mt-1.5 text-sm text-muted-foreground">{subtitle}</p>}
          </div>

          {children}
        </div>

        {footer && <div className="mt-6 text-center text-sm text-muted-foreground">{footer}</div>}
      </motion.div>
    </div>
  )
}

export default AuthLayout
