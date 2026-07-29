import { useMemo, useState } from 'react'
import {
  BookOpen,
  CalendarClock,
  ChevronDown,
  ClipboardList,
  Clock,
  Coffee,
  Flag,
  RotateCcw,
  Target,
} from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import {
  addMinutesToTime,
  cn,
  formatDate,
  formatHours,
  formatMinutes,
  formatTime,
  parseISODate,
} from '@/lib/utils'

/**
 * Priority is judged against the rest of *this* plan, not a fixed scale.
 *
 * The engine's raw score depends on how many subjects there are and how close
 * the exams happen to be, so absolute cut-offs would mark every session
 * "normal" for a student with no exams booked yet, which tells them nothing.
 * Fixed commitments (revision, admissions practice, timed papers, exam-day
 * reviews) are always high: they cannot be moved. Study blocks are ranked
 * against the highest-scoring study block in the plan.
 */
const FIXED_KINDS = new Set(['revision', 'admission', 'past_paper'])

function buildPriority(sessions) {
  const studyScores = sessions
    .filter((s) => !FIXED_KINDS.has(s.kind) && s.kind !== 'break')
    .map((s) => s.priority_score ?? 0)
  const top = studyScores.length ? Math.max(...studyScores) : 0

  return (session) => {
    if (session.kind === 'break') return 'normal'
    if (FIXED_KINDS.has(session.kind)) return 'high'
    if (!top) return 'normal'
    const ratio = (session.priority_score ?? 0) / top
    if (ratio >= 0.85) return 'high'
    if (ratio >= 0.6) return 'medium'
    return 'normal'
  }
}

const PRIORITY = {
  high: { label: 'High', dot: 'bg-destructive', text: 'text-destructive' },
  medium: { label: 'Medium', dot: 'bg-accent', text: 'text-accent-foreground dark:text-accent' },
  normal: { label: 'Normal', dot: 'bg-muted-foreground/50', text: 'text-muted-foreground' },
}

const KIND = {
  study: { label: 'Study', icon: BookOpen },
  revision: { label: 'Revision', icon: RotateCcw },
  admission: { label: 'Admissions', icon: Target },
  past_paper: { label: 'Past paper', icon: ClipboardList },
  break: { label: 'Break', icon: Coffee },
}

const DAYS_SHOWN = 7

function groupByDay(sessions) {
  const days = new Map()
  for (const session of sessions) {
    if (!days.has(session.session_date)) days.set(session.session_date, [])
    days.get(session.session_date).push(session)
  }
  return [...days.entries()]
    .sort(([a], [b]) => (a < b ? -1 : 1))
    .map(([date, items]) => ({
      date,
      sessions: items.slice().sort((a, b) => a.start_time.localeCompare(b.start_time)),
      minutes: items.reduce((total, s) => total + (s.duration_minutes || 0), 0),
    }))
}

function dayLabel(iso) {
  const date = parseISODate(iso)
  if (!date) return iso
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const diff = Math.round((date - today) / 86400000)
  if (diff === 0) return 'Today'
  if (diff === 1) return 'Tomorrow'
  return date.toLocaleDateString('en-GB', { weekday: 'long' })
}

/** One scheduled block: when, what subject, what to do, how urgent. */
function ScheduleBlock({ session, priorityOf }) {
  const priority = PRIORITY[priorityOf(session)]
  const kind = KIND[session.kind] || KIND.study
  const KindIcon = kind.icon
  const ends = addMinutesToTime(session.start_time, session.duration_minutes)

  return (
    <li className="relative flex gap-3 py-3 pl-3 sm:gap-4 sm:pl-4">
      <span
        aria-hidden="true"
        className="absolute inset-y-0 left-0 w-0.5 rounded-full"
        style={{ backgroundColor: session.subject_colour || undefined }}
      />

      {/* Timeframe */}
      <div className="w-14 shrink-0 pt-0.5 sm:w-16">
        <p className="font-display text-sm font-bold tabular-nums leading-none">
          {formatTime(session.start_time)}
        </p>
        <p className="mt-1 text-[11px] tabular-nums text-muted-foreground">{ends}</p>
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-1.5">
          {session.subject_name && (
            <span
              className="inline-flex items-center gap-1.5 rounded-md px-1.5 py-0.5 text-[11px] font-semibold"
              style={{
                backgroundColor: `${session.subject_colour || '#64748b'}1f`,
                color: session.subject_colour || undefined,
              }}
            >
              <span
                className="size-1.5 rounded-full"
                style={{ backgroundColor: session.subject_colour || undefined }}
              />
              {session.subject_name}
            </span>
          )}
          <Badge variant="outline" className="gap-1 text-[11px]">
            <KindIcon />
            {kind.label}
          </Badge>
          <span className="inline-flex items-center gap-1 text-[11px] text-muted-foreground">
            <Clock className="size-3" />
            {formatMinutes(session.duration_minutes)}
          </span>
        </div>

        {/* The task itself */}
        <p className="mt-1.5 text-sm font-semibold leading-snug">{session.title}</p>
        {session.description && (
          <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">
            {session.description}
          </p>
        )}
      </div>

      {/* Priority marker */}
      <div className="flex shrink-0 flex-col items-end gap-1 pt-0.5">
        <span className={cn('flex items-center gap-1 text-[11px] font-semibold', priority.text)}>
          <span className={cn('size-1.5 rounded-full', priority.dot)} />
          <span className="hidden sm:inline">{priority.label}</span>
        </span>
      </div>
    </li>
  )
}

/**
 * The output of a plan generation, laid out as a schedule rather than a
 * paragraph: one section per day, each block carrying its timeframe, subject,
 * task and priority.
 */
export function GeneratedPlan({ plan, onOpenWeek }) {
  const [expanded, setExpanded] = useState(false)
  const days = useMemo(() => groupByDay(plan?.sessions || []), [plan])
  const priorityOf = useMemo(() => buildPriority(plan?.sessions || []), [plan])

  if (!plan) return null

  const shown = expanded ? days : days.slice(0, DAYS_SHOWN)
  const hidden = days.length - shown.length
  const highCount = (plan.sessions || []).filter((s) => priorityOf(s) === 'high').length

  return (
    <Card className="overflow-hidden border-primary/30">
      <div className="border-b border-border bg-primary/5 p-4 sm:p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-primary">
              <CalendarClock className="size-4" />
              Your plan is ready
            </p>
            <h2 className="mt-1 font-display text-lg font-bold tracking-tight sm:text-xl">
              {formatDate(plan.start_date)} to {formatDate(plan.end_date)}
            </h2>
          </div>
          {onOpenWeek && (
            <Button variant="outline" size="sm" onClick={onOpenWeek}>
              Open week view
            </Button>
          )}
        </div>

        <dl className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4 sm:gap-3">
          {[
            ['Days', plan.horizon_days],
            ['Sessions', (plan.sessions || []).length],
            ['Total time', formatHours(plan.total_hours)],
            ['High priority', highCount],
          ].map(([label, value]) => (
            <div key={label} className="rounded-lg bg-card px-3 py-2">
              <dt className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                {label}
              </dt>
              <dd className="mt-0.5 font-display text-base font-bold tabular-nums">{value}</dd>
            </div>
          ))}
        </dl>

        {plan.strategy && (
          <p className="mt-4 text-sm leading-relaxed text-muted-foreground">{plan.strategy}</p>
        )}

        {plan.focus_notes?.length > 0 && (
          <ul className="mt-3 space-y-1.5">
            {plan.focus_notes.map((note) => (
              <li key={note} className="flex items-start gap-2 text-xs text-muted-foreground">
                <Flag className="mt-0.5 size-3.5 shrink-0 text-primary" />
                {note}
              </li>
            ))}
          </ul>
        )}
      </div>

      <CardContent className="p-0">
        {days.length === 0 ? (
          <p className="p-5 text-sm text-muted-foreground">
            No sessions were scheduled. Upload a syllabus for each subject so there are
            topics to plan around.
          </p>
        ) : (
          <>
            {shown.map((day) => (
              <section key={day.date} className="border-b border-border/70 last:border-0">
                <header className="flex items-center justify-between gap-3 bg-muted/40 px-4 py-2">
                  <h3 className="text-sm font-bold">
                    {dayLabel(day.date)}{' '}
                    <span className="font-medium text-muted-foreground">
                      {formatDate(day.date)}
                    </span>
                  </h3>
                  <span className="shrink-0 text-xs font-semibold tabular-nums text-muted-foreground">
                    {day.sessions.length} · {formatMinutes(day.minutes)}
                  </span>
                </header>
                <ul className="divide-y divide-border/60 px-2 sm:px-3">
                  {day.sessions.map((session) => (
                    <ScheduleBlock key={session.id} session={session} priorityOf={priorityOf} />
                  ))}
                </ul>
              </section>
            ))}

            {hidden > 0 && (
              <div className="p-3">
                <Button
                  variant="ghost"
                  className="w-full"
                  onClick={() => setExpanded(true)}
                >
                  <ChevronDown /> Show the remaining {hidden} days
                </Button>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}

export default GeneratedPlan
