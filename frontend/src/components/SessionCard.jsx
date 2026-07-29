import { motion } from 'framer-motion'
import {
  BookOpen,
  Check,
  Clock,
  FileText,
  MoreVertical,
  Play,
  RotateCcw,
  SkipForward,
  Target,
  Trash2,
} from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  SESSION_KIND_LABELS,
  addMinutesToTime,
  cn,
  formatMinutes,
  formatTime,
} from '@/lib/utils'

const KIND_META = {
  study: { icon: BookOpen, variant: 'default' },
  revision: { icon: RotateCcw, variant: 'violet' },
  admission: { icon: Target, variant: 'warning' },
  past_paper: { icon: FileText, variant: 'info' },
  break: { icon: Clock, variant: 'secondary' },
}

const STATUS_META = {
  completed: { label: 'Done', variant: 'success' },
  missed: { label: 'Missed', variant: 'destructive' },
  skipped: { label: 'Skipped', variant: 'outline' },
}

/** One block on the timetable, with its complete / skip / delete actions. */
export function SessionCard({
  session,
  onComplete,
  onSkip,
  onReset,
  onDelete,
  onStart,
  compact = false,
  index = 0,
}) {
  const kind = KIND_META[session.kind] || KIND_META.study
  const KindIcon = kind.icon
  const status = STATUS_META[session.status]
  const done = session.status === 'completed'
  const colour = session.subject_colour || '#6366f1'

  return (
    <motion.article
      layout
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: Math.min(index * 0.04, 0.3) }}
      className={cn(
        'group relative flex gap-3 overflow-hidden rounded-2xl border border-border/70 bg-card p-4 shadow-soft transition-all',
        'hover:border-border hover:shadow-card',
        done && 'opacity-70',
        session.status === 'missed' && 'border-rose-300/60 dark:border-rose-900/60',
      )}
    >
      <span
        className="absolute inset-y-0 left-0 w-1.5"
        style={{ backgroundColor: colour }}
        aria-hidden="true"
      />

      <div className="ml-1.5 flex w-14 shrink-0 flex-col items-center pt-0.5 text-center">
        <span className="font-display text-sm font-bold tabular-nums">
          {formatTime(session.start_time)}
        </span>
        <span className="text-[11px] text-muted-foreground">
          {addMinutesToTime(session.start_time, session.duration_minutes)}
        </span>
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-1.5">
          <Badge variant={kind.variant} className="gap-1">
            <KindIcon />
            {SESSION_KIND_LABELS[session.kind] || session.kind}
          </Badge>
          {status && <Badge variant={status.variant}>{status.label}</Badge>}
          <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
            <Clock className="size-3" />
            {formatMinutes(session.duration_minutes)}
          </span>
        </div>

        <h4
          className={cn(
            'mt-1.5 text-sm font-semibold leading-snug',
            done && 'line-through decoration-muted-foreground/60',
          )}
        >
          {session.title}
        </h4>

        {!compact && session.description && (
          <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">
            {session.description}
          </p>
        )}
      </div>

      <div className="flex shrink-0 items-start gap-1">
        {!done && onStart && (
          <Button
            size="icon-sm"
            variant="ghost"
            onClick={() => onStart(session)}
            aria-label={`Start "${session.title}" with a timer`}
            title="Start with a timer"
          >
            <Play />
          </Button>
        )}
        {!done && onComplete && (
          <Button
            size="icon-sm"
            variant="subtle"
            onClick={() => onComplete(session)}
            aria-label={`Mark "${session.title}" complete`}
            title="Mark complete"
          >
            <Check />
          </Button>
        )}
        {(onSkip || onDelete || onReset) && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                size="icon-sm"
                variant="ghost"
                aria-label={`More actions for "${session.title}"`}
              >
                <MoreVertical />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {done && onReset && (
                <DropdownMenuItem onSelect={() => onReset(session)}>
                  <RotateCcw /> Mark as not done
                </DropdownMenuItem>
              )}
              {!done && onSkip && (
                <DropdownMenuItem onSelect={() => onSkip(session)}>
                  <SkipForward /> Skip this session
                </DropdownMenuItem>
              )}
              {onDelete && (
                <>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem destructive onSelect={() => onDelete(session)}>
                    <Trash2 /> Remove
                  </DropdownMenuItem>
                </>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>
    </motion.article>
  )
}

export default SessionCard
