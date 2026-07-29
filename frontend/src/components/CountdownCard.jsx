import { CalendarClock, MapPin } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { ProgressRing } from '@/components/ui/progress'
import { cn, formatDate, formatTime, pluralise } from '@/lib/utils'

function urgency(days) {
  if (days <= 3) return { variant: 'destructive', label: 'Imminent' }
  if (days <= 14) return { variant: 'warning', label: 'Close' }
  if (days <= 45) return { variant: 'info', label: 'Approaching' }
  return { variant: 'secondary', label: 'Scheduled' }
}

/** Exam countdown tile — used for both school and admissions exams. */
export function CountdownCard({ exam, className }) {
  const days = exam.days_remaining ?? 0
  const tone = urgency(days)
  const colour = exam.subject_colour || '#6366f1'

  return (
    <div
      className={cn(
        'card-hover relative flex items-center gap-4 overflow-hidden rounded-2xl border border-border/70 bg-card p-4 shadow-soft',
        className,
      )}
    >
      <span
        className="absolute inset-y-0 left-0 w-1.5"
        style={{ backgroundColor: colour }}
        aria-hidden="true"
      />

      <div className="ml-1.5 min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-1.5">
          <Badge variant={tone.variant}>
            {days === 0 ? 'Today' : pluralise(days, 'day')}
          </Badge>
          {exam.exam_board && <Badge variant="outline">{exam.exam_board}</Badge>}
          {exam.kind === 'admission' && <Badge variant="violet">Admissions</Badge>}
        </div>

        <h4 className="mt-1.5 truncate text-sm font-semibold">{exam.title}</h4>

        <p className="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1">
            <CalendarClock className="size-3" />
            {formatDate(exam.exam_date, {
              weekday: 'short',
              day: 'numeric',
              month: 'short',
            })}
            {exam.exam_time ? ` · ${formatTime(exam.exam_time)}` : ''}
          </span>
          {exam.location && (
            <span className="inline-flex items-center gap-1">
              <MapPin className="size-3" />
              {exam.location}
            </span>
          )}
        </p>
      </div>

      <ProgressRing
        value={exam.preparation_percentage || 0}
        size={52}
        stroke={5}
        colour={colour}
      />
    </div>
  )
}

export default CountdownCard
