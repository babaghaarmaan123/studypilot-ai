import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  CheckCircle2,
  Clock,
  ListChecks,
  Repeat,
  Trash2,
  TrendingUp,
} from 'lucide-react'

import { useToast } from '@/context/ToastContext'
import { useFetch } from '@/hooks/useFetch'
import api, { ApiError } from '@/lib/api'
import {
  REVISION_INTERVAL_LABELS,
  daysBetween,
  formatDate,
  formatMinutes,
  relativeDays,
  toISODate,
} from '@/lib/utils'

import { PageHeader } from '@/components/PageHeader'
import { StatCard } from '@/components/StatCard'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { EmptyState } from '@/components/ui/empty-state'
import { SkeletonList, SkeletonStats } from '@/components/ui/skeleton'

const RECALL_OPTIONS = [
  { value: 1, label: 'Blanked' },
  { value: 2, label: 'Struggled' },
  { value: 3, label: 'Okay' },
  { value: 4, label: 'Good' },
  { value: 5, label: 'Perfect' },
]

function RevisionRow({ entry, onComplete, onSnooze, onDelete, index = 0 }) {
  const colour = entry.subject_colour || '#6366f1'
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: Math.min(index * 0.03, 0.3) }}
      className="relative flex items-center gap-3 overflow-hidden rounded-2xl border border-border/70 bg-card p-4 shadow-soft"
    >
      <span className="absolute inset-y-0 left-0 w-1.5" style={{ backgroundColor: colour }} />
      <div className="ml-1.5 min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-1.5">
          <Badge variant="violet">{REVISION_INTERVAL_LABELS[entry.interval_label] || entry.interval_label}</Badge>
          {entry.is_overdue && <Badge variant="destructive">Overdue</Badge>}
          <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
            <Clock className="size-3" /> {formatMinutes(entry.duration_minutes)}
          </span>
        </div>
        <h4 className="mt-1 truncate text-sm font-semibold">{entry.topic_name}</h4>
        <p className="text-xs text-muted-foreground">
          {entry.subject_name} · {formatDate(entry.scheduled_date)} ·{' '}
          {relativeDays(daysBetween(toISODate(new Date()), entry.scheduled_date))}
        </p>
      </div>
      <div className="flex shrink-0 items-center gap-1.5">
        {onSnooze && (
          <Button variant="ghost" size="sm" onClick={() => onSnooze(entry)}>
            Snooze
          </Button>
        )}
        {onComplete && (
          <Button variant="subtle" size="sm" onClick={() => onComplete(entry)}>
            <CheckCircle2 /> Revise
          </Button>
        )}
        {onDelete && (
          <Button variant="ghost" size="icon-sm" onClick={() => onDelete(entry)} aria-label="Remove">
            <Trash2 />
          </Button>
        )}
      </div>
    </motion.div>
  )
}

export default function Revision() {
  const { toast } = useToast()
  const { data: due, loading: dueLoading, reload: reloadDue } = useFetch(
    () => api.revision.due(),
    [],
  )
  const { data: upcoming, loading: upcomingLoading, reload: reloadUpcoming } = useFetch(
    () => api.revision.list(30),
    [],
  )
  const { data: stats, reload: reloadStats } = useFetch(() => api.revision.stats(), [])

  const [ratingTarget, setRatingTarget] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  const refreshAll = () => {
    reloadDue({ silent: true })
    reloadUpcoming({ silent: true })
    reloadStats({ silent: true })
  }

  const completeWithRating = async (rating) => {
    setSubmitting(true)
    try {
      await api.revision.complete(ratingTarget.id, rating)
      toast.success('Revision logged')
      setRatingTarget(null)
      refreshAll()
    } catch (err) {
      toast.error('Could not save that', err instanceof ApiError ? err.message : undefined)
    } finally {
      setSubmitting(false)
    }
  }

  const snooze = async (entry) => {
    try {
      await api.revision.snooze(entry.id, 1)
      toast.info('Pushed back a day')
      refreshAll()
    } catch (err) {
      toast.error('Could not snooze', err instanceof ApiError ? err.message : undefined)
    }
  }

  const remove = async (entry) => {
    try {
      await api.revision.remove(entry.id)
      refreshAll()
    } catch (err) {
      toast.error('Could not remove', err instanceof ApiError ? err.message : undefined)
    }
  }

  const upcomingPending = (upcoming || []).filter(
    (e) => e.status === 'pending' && !e.is_due,
  )

  return (
    <div className="space-y-8">
      <PageHeader
        title="Revision"
        description="Spaced-repetition checkpoints at 2, 7 and 14 days, plus a final pass before each exam."
        icon={Repeat}
      />

      {!stats ? (
        <SkeletonStats count={4} />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Total checkpoints" value={Math.round(stats.total)} icon={ListChecks} tone="indigo" />
          <StatCard label="Completed" value={Math.round(stats.completed)} icon={CheckCircle2} tone="emerald" />
          <StatCard label="Pending" value={Math.round(stats.pending)} icon={Clock} tone="sky" />
          <StatCard label="Completion rate" value={`${stats.rate}%`} progress={stats.rate} icon={TrendingUp} tone="violet" />
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="size-4.5 text-primary" /> Due now
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2.5">
          {dueLoading ? (
            <SkeletonList rows={3} />
          ) : due?.length ? (
            due.map((entry, index) => (
              <RevisionRow
                key={entry.id}
                entry={entry}
                index={index}
                onComplete={(e) => setRatingTarget(e)}
                onSnooze={snooze}
                onDelete={remove}
              />
            ))
          ) : (
            <EmptyState
              icon={CheckCircle2}
              title="Nothing due right now"
              description="You're fully caught up on revision."
              className="py-10"
            />
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Upcoming (next 30 days)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2.5">
          {upcomingLoading ? (
            <SkeletonList rows={4} />
          ) : upcomingPending.length ? (
            upcomingPending.map((entry, index) => (
              <RevisionRow key={entry.id} entry={entry} index={index} onDelete={remove} />
            ))
          ) : (
            <EmptyState
              icon={Repeat}
              title="No upcoming revisions scheduled"
              description="Complete topics in your syllabus to automatically book revision checkpoints."
              className="py-10"
            />
          )}
        </CardContent>
      </Card>

      <Dialog open={Boolean(ratingTarget)} onOpenChange={(open) => !open && setRatingTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>How well did you recall it?</DialogTitle>
            <DialogDescription>
              {ratingTarget?.topic_name} — rate 1 to 5. A low score books a quick retry in two
              days and reopens the topic.
            </DialogDescription>
          </DialogHeader>
          <div className="grid grid-cols-5 gap-2">
            {RECALL_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                disabled={submitting}
                onClick={() => completeWithRating(opt.value)}
                className="flex flex-col items-center gap-1.5 rounded-2xl border-2 border-border px-2 py-3 text-center transition-all hover:border-primary hover:bg-primary/5 disabled:opacity-50"
              >
                <span className="font-display text-lg font-bold text-primary">{opt.value}</span>
                <span className="text-[11px] text-muted-foreground">{opt.label}</span>
              </button>
            ))}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRatingTarget(null)}>
              Cancel
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
