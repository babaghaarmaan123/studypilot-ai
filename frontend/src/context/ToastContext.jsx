import { createContext, useCallback, useContext, useMemo, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { AlertTriangle, CheckCircle2, Info, X, XCircle } from 'lucide-react'

import { cn } from '@/lib/utils'

const ToastContext = createContext(null)

const VARIANTS = {
  success: {
    icon: CheckCircle2,
    accent: 'bg-emerald-500',
    iconClass: 'text-emerald-600 dark:text-emerald-400',
  },
  error: {
    icon: XCircle,
    accent: 'bg-rose-500',
    iconClass: 'text-rose-600 dark:text-rose-400',
  },
  warning: {
    icon: AlertTriangle,
    accent: 'bg-amber-500',
    iconClass: 'text-amber-600 dark:text-amber-400',
  },
  info: { icon: Info, accent: 'bg-indigo-500', iconClass: 'text-indigo-600 dark:text-indigo-400' },
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const timers = useRef(new Map())

  const dismiss = useCallback((id) => {
    setToasts((current) => current.filter((t) => t.id !== id))
    const timer = timers.current.get(id)
    if (timer) {
      clearTimeout(timer)
      timers.current.delete(id)
    }
  }, [])

  const push = useCallback(
    (toast) => {
      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
      const entry = { id, variant: 'info', duration: 4500, ...toast }
      setToasts((current) => [...current.slice(-3), entry])
      if (entry.duration > 0) {
        timers.current.set(
          id,
          setTimeout(() => dismiss(id), entry.duration),
        )
      }
      return id
    },
    [dismiss],
  )

  const toast = useMemo(
    () => ({
      show: push,
      success: (title, description) => push({ variant: 'success', title, description }),
      error: (title, description) =>
        push({ variant: 'error', title, description, duration: 6000 }),
      warning: (title, description) => push({ variant: 'warning', title, description }),
      info: (title, description) => push({ variant: 'info', title, description }),
      dismiss,
    }),
    [push, dismiss],
  )

  // Exposed as `{ toast }` because every consumer destructures it:
  // `const { toast } = useToast()`.
  const value = useMemo(() => ({ toast }), [toast])

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        className="pointer-events-none fixed inset-x-0 bottom-0 z-[100] flex flex-col items-center gap-2 p-4 sm:inset-x-auto sm:right-0 sm:top-0 sm:items-end sm:p-6"
        role="region"
        aria-label="Notifications"
      >
        <AnimatePresence initial={false}>
          {toasts.map((item) => {
            const meta = VARIANTS[item.variant] || VARIANTS.info
            const Icon = meta.icon
            return (
              <motion.div
                key={item.id}
                layout
                initial={{ opacity: 0, y: 16, scale: 0.96 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, x: 24, scale: 0.96 }}
                transition={{ type: 'spring', stiffness: 380, damping: 30 }}
                className="pointer-events-auto relative flex w-full max-w-sm gap-3 overflow-hidden rounded-2xl border border-border bg-card p-4 pr-10 shadow-lift"
                role="status"
                aria-live="polite"
              >
                <span
                  className={cn('absolute inset-y-0 left-0 w-1', meta.accent)}
                  aria-hidden="true"
                />
                <Icon className={cn('mt-0.5 size-5 shrink-0', meta.iconClass)} />
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold leading-snug">{item.title}</p>
                  {item.description && (
                    <p className="mt-0.5 break-words text-xs text-muted-foreground">
                      {item.description}
                    </p>
                  )}
                </div>
                <button
                  type="button"
                  onClick={() => dismiss(item.id)}
                  className="absolute right-2.5 top-2.5 rounded-lg p-1 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                  aria-label="Dismiss notification"
                >
                  <X className="size-3.5" />
                </button>
              </motion.div>
            )
          })}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const context = useContext(ToastContext)
  if (!context) throw new Error('useToast must be used inside <ToastProvider>')
  return context
}
