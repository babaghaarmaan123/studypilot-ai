import { AlarmClock, BellRing, Clock, Play } from 'lucide-react'

import { useStudySession, sessionStartAt } from '@/context/StudySessionContext'
import { SESSION_KIND_LABELS, addMinutesToTime, formatMinutes, formatTime } from '@/lib/utils'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

/** Minutes until `session` starts, floored at 0. */
function minutesUntil(session) {
  const start = sessionStartAt(session)
  if (!start) return 0
  return Math.max(0, Math.round((start.getTime() - Date.now()) / 60_000))
}

/**
 * The two reminders every session gets: one five minutes before it starts and
 * one when it starts. Starting from here also starts the session timer.
 */
export function SessionReminderDialog() {
  const { alert, dismissAlert, startTimer } = useStudySession()
  const session = alert?.session
  const soon = alert?.kind === 'soon'

  if (!session) return null

  const Icon = soon ? BellRing : AlarmClock
  const away = minutesUntil(session)

  return (
    <Dialog open onOpenChange={(open) => !open && dismissAlert()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <span className="mb-1 grid size-11 place-items-center rounded-2xl bg-primary/10 text-primary">
            <Icon className="size-5.5" />
          </span>
          <DialogTitle>
            {soon
              ? `Starting in ${away || 5} ${away === 1 ? 'minute' : 'minutes'}`
              : 'Time to start studying'}
          </DialogTitle>
          <DialogDescription>
            {soon
              ? 'Get your notes and a glass of water ready.'
              : 'Your scheduled session begins now.'}
          </DialogDescription>
        </DialogHeader>

        <div className="rounded-2xl border border-border/70 bg-muted/40 p-4">
          <div className="flex flex-wrap items-center gap-1.5">
            <Badge variant="outline">
              {SESSION_KIND_LABELS[session.kind] || session.kind}
            </Badge>
            {session.subject_name && (
              <Badge variant="secondary">{session.subject_name}</Badge>
            )}
            <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
              <Clock className="size-3" />
              {formatTime(session.start_time)}–
              {addMinutesToTime(session.start_time, session.duration_minutes)} ·{' '}
              {formatMinutes(session.duration_minutes)}
            </span>
          </div>
          <p className="mt-2 text-sm font-semibold leading-snug">{session.title}</p>
          {session.description && (
            <p className="mt-1 text-xs text-muted-foreground">{session.description}</p>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={dismissAlert}>
            {soon ? 'Got it' : 'Not now'}
          </Button>
          <Button
            onClick={() => {
              startTimer(session)
              dismissAlert()
            }}
          >
            <Play /> Start session
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export default SessionReminderDialog
