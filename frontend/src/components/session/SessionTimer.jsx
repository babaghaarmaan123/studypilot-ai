import { AnimatePresence, motion } from 'framer-motion'
import { AlarmClock, Check, Pause, Play, Plus, X } from 'lucide-react'

import { useStudySession } from '@/context/StudySessionContext'
import { useToast } from '@/context/ToastContext'
import { usePending } from '@/hooks/useFetch'
import api, { ApiError } from '@/lib/api'
import { cn } from '@/lib/utils'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

function clock(ms) {
  const total = Math.max(0, Math.round(ms / 1000))
  const minutes = Math.floor(total / 60)
  const seconds = total % 60
  return `${minutes}:${`${seconds}`.padStart(2, '0')}`
}

/**
 * The running-session bar: a countdown that can be paused and resumed, and the
 * alarm dialog when the session reaches the time it was scheduled to end.
 *
 * Sits bottom-left so it never covers the toast stack.
 */
export function SessionTimer() {
  const {
    timer,
    ringing,
    pauseTimer,
    resumeTimer,
    stopTimer,
    extendTimer,
    dismissAlarm,
    refresh,
  } = useStudySession()
  const { toast } = useToast()
  const [completing, wrapComplete] = usePending()

  const complete = () =>
    wrapComplete(async () => {
      const session = timer?.session
      if (!session) return
      try {
        await api.plans.completeSession(session.id)
        dismissAlarm()
        await refresh()
        toast.success('Session complete', session.title)
      } catch (err) {
        toast.error(
          'Could not mark that complete',
          err instanceof ApiError ? err.message : undefined,
        )
      }
    })

  const total = (timer?.session?.duration_minutes || 1) * 60_000
  const progress = timer ? Math.min(100, ((total - timer.remainingMs) / total) * 100) : 0

  return (
    <>
      <AnimatePresence>
        {timer && !ringing && (
          <motion.aside
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            transition={{ type: 'spring', stiffness: 360, damping: 30 }}
            className="fixed inset-x-4 bottom-20 z-40 sm:inset-x-auto sm:bottom-6 sm:left-6 sm:w-80"
            role="region"
            aria-label="Study session timer"
          >
            <div className="overflow-hidden rounded-2xl border border-border bg-card shadow-lift">
              <div className="flex items-center gap-3 p-4">
                <span
                  className={cn(
                    'grid size-11 shrink-0 place-items-center rounded-xl font-display text-sm font-bold tabular-nums',
                    timer.paused
                      ? 'bg-muted text-muted-foreground'
                      : 'bg-primary/10 text-primary',
                  )}
                >
                  {clock(timer.remainingMs)}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold">{timer.session.title}</p>
                  <p className="text-xs text-muted-foreground">
                    {timer.paused ? 'Paused' : 'In progress'}
                    {timer.session.subject_name ? ` · ${timer.session.subject_name}` : ''}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-1">
                  <Button
                    size="icon-sm"
                    variant="subtle"
                    onClick={timer.paused ? resumeTimer : pauseTimer}
                    aria-label={timer.paused ? 'Resume timer' : 'Pause timer'}
                    title={timer.paused ? 'Resume' : 'Pause'}
                  >
                    {timer.paused ? <Play /> : <Pause />}
                  </Button>
                  <Button
                    size="icon-sm"
                    variant="ghost"
                    onClick={stopTimer}
                    aria-label="Stop timer"
                    title="Stop"
                  >
                    <X />
                  </Button>
                </div>
              </div>
              <div className="h-1 bg-muted">
                <div
                  className="h-full bg-primary transition-[width] duration-500"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
          </motion.aside>
        )}
      </AnimatePresence>

      <Dialog open={Boolean(ringing && timer)} onOpenChange={(open) => !open && dismissAlarm()}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <motion.span
              animate={{ rotate: [0, -12, 12, -8, 8, 0] }}
              transition={{ duration: 1, repeat: Infinity, repeatDelay: 0.6 }}
              className="mb-1 grid size-11 place-items-center rounded-2xl bg-amber-500/15 text-amber-600 dark:text-amber-400"
            >
              <AlarmClock className="size-5.5" />
            </motion.span>
            <DialogTitle>Time’s up</DialogTitle>
            <DialogDescription>
              {timer?.session?.title} has reached the end of its slot.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="sm:flex-wrap">
            <Button variant="outline" onClick={dismissAlarm}>
              <X /> Dismiss
            </Button>
            <Button variant="outline" onClick={() => extendTimer(5)}>
              <Plus /> 5 more minutes
            </Button>
            <Button onClick={complete} loading={completing}>
              <Check /> Mark complete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}

export default SessionTimer
