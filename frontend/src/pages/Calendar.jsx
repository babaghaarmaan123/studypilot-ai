import { useMemo, useState } from 'react'
import ReactCalendar from 'react-calendar'
import 'react-calendar/dist/Calendar.css'
import { Calendar as CalendarIcon, Plus } from 'lucide-react'

import { useToast } from '@/context/ToastContext'
import { useFetch, usePending } from '@/hooks/useFetch'
import api, { ApiError } from '@/lib/api'
import { formatLongDate, toISODate } from '@/lib/utils'

import { PageHeader } from '@/components/PageHeader'
import { SessionCard } from '@/components/SessionCard'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { EmptyState } from '@/components/ui/empty-state'
import { Field } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'

const DOT_TONE = {
  done: 'bg-emerald-500',
  missed: 'bg-rose-500',
  pending: 'bg-indigo-500',
}

function dayTone(day) {
  if (!day?.sessions?.length) return null
  if (day.sessions.every((s) => s.status === 'completed')) return 'done'
  if (day.sessions.some((s) => s.status === 'missed')) return 'missed'
  return 'pending'
}

export default function CalendarPage() {
  const { toast } = useToast()
  const [activeDate, setActiveDate] = useState(new Date())
  const [selectedDate, setSelectedDate] = useState(new Date())
  const [dialogOpen, setDialogOpen] = useState(false)
  const [form, setForm] = useState({ title: '', subject_id: '', start_time: '17:00', duration_minutes: 60 })
  const [pending, wrap] = usePending()

  const { data: subjects } = useFetch(() => api.subjects.list(), [])
  const { data: month, loading, reload } = useFetch(
    () => api.plans.month(activeDate.getFullYear(), activeDate.getMonth() + 1),
    [activeDate.getFullYear(), activeDate.getMonth()],
  )

  const selectedIso = toISODate(selectedDate)
  const selectedDay = useMemo(
    () => month?.find((d) => d.date === selectedIso) || null,
    [month, selectedIso],
  )

  const act = async (session, action) => {
    try {
      if (action === 'complete') await api.plans.completeSession(session.id)
      if (action === 'skip') await api.plans.skipSession(session.id)
      if (action === 'reset') await api.plans.resetSession(session.id)
      if (action === 'delete') await api.plans.removeSession(session.id)
      reload({ silent: true })
    } catch (err) {
      toast.error('Could not update session', err instanceof ApiError ? err.message : undefined)
    }
  }

  const submit = () =>
    wrap(async () => {
      try {
        await api.plans.createSession({
          title: form.title.trim(),
          subject_id: form.subject_id ? Number(form.subject_id) : null,
          session_date: selectedIso,
          start_time: form.start_time,
          duration_minutes: Number(form.duration_minutes),
          kind: 'study',
        })
        toast.success('Session added')
        setDialogOpen(false)
        setForm({ title: '', subject_id: '', start_time: '17:00', duration_minutes: 60 })
        reload()
      } catch (err) {
        toast.error('Could not add session', err instanceof ApiError ? err.message : undefined)
      }
    })

  return (
    <div className="space-y-6">
      <PageHeader
        title="Calendar"
        description="Every session, revision and exam in one month view."
        icon={CalendarIcon}
      />

      {/* min-w-0 on the grid children: a grid track is auto-sized by default,
          so anything inside with an intrinsic width would widen the column
          rather than being made to fit. */}
      <div className="grid gap-4 sm:gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
        <Card className="min-w-0">
          {/* Tighter padding on a phone: at 375px, every 4px of card padding
              costs half a pixel off each of the seven columns, and the tiles
              have to stay at least 44px wide to be comfortably tappable. */}
          <CardContent className="p-2 pt-3 sm:p-6">
            {loading && !month ? (
              <Skeleton className="h-[380px] w-full rounded-2xl" />
            ) : (
              <ReactCalendar
                value={selectedDate}
                onChange={setSelectedDate}
                onActiveStartDateChange={({ activeStartDate }) =>
                  activeStartDate && setActiveDate(activeStartDate)
                }
                // Monday-first, and short weekday initials so seven columns fit
                // a 375px screen without the labels being clipped.
                locale="en-GB"
                formatShortWeekday={(_locale, date) =>
                  ['S', 'M', 'T', 'W', 'T', 'F', 'S'][date.getDay()]
                }
                prev2Label={null}
                next2Label={null}
                tileContent={({ date, view }) => {
                  if (view !== 'month') return null
                  const day = month?.find((d) => d.date === toISODate(date))
                  const tone = dayTone(day)
                  if (!tone) return null
                  return (
                    <span
                      className={`cal-dot pointer-events-none absolute bottom-1 left-1/2 size-1.5 -translate-x-1/2 rounded-full ${DOT_TONE[tone]}`}
                    />
                  )
                }}
              />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{formatLongDate(selectedIso)}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Button
              variant="outline"
              size="sm"
              className="w-full"
              onClick={() => setDialogOpen(true)}
            >
              <Plus /> Add session on this day
            </Button>

            {selectedDay?.sessions?.length ? (
              selectedDay.sessions.map((session, index) => (
                <SessionCard
                  key={session.id}
                  session={session}
                  index={index}
                  compact
                  onComplete={(s) => act(s, 'complete')}
                  onSkip={(s) => act(s, 'skip')}
                  onReset={(s) => act(s, 'reset')}
                  onDelete={(s) => act(s, 'delete')}
                />
              ))
            ) : (
              <EmptyState
                icon={CalendarIcon}
                title="Nothing scheduled"
                description="A free day. Add a session if you want one."
                className="py-8"
              />
            )}
          </CardContent>
        </Card>
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add a session · {formatLongDate(selectedIso)}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <Field label="Title" required>
              <Input
                value={form.title}
                onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
                placeholder="e.g. Past paper practice"
              />
            </Field>
            <Field label="Subject">
              <Select
                value={form.subject_id || undefined}
                onValueChange={(v) => setForm((f) => ({ ...f, subject_id: v }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Optional" />
                </SelectTrigger>
                <SelectContent>
                  {(subjects || []).map((s) => (
                    <SelectItem key={s.id} value={String(s.id)}>
                      {s.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Start time">
                <Input
                  type="time"
                  value={form.start_time}
                  onChange={(e) => setForm((f) => ({ ...f, start_time: e.target.value }))}
                />
              </Field>
              <Field label="Minutes">
                <Input
                  type="number"
                  min={10}
                  max={480}
                  value={form.duration_minutes}
                  onChange={(e) => setForm((f) => ({ ...f, duration_minutes: e.target.value }))}
                />
              </Field>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={submit} loading={pending} disabled={!form.title.trim()}>
              Add session
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
