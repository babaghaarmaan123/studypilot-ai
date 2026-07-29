import { useCallback, useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { CalendarClock, CalendarPlus, ChevronLeft, ChevronRight, Plus } from 'lucide-react'

import { useStudySession } from '@/context/StudySessionContext'
import { useToast } from '@/context/ToastContext'
import { useFetch, usePending } from '@/hooks/useFetch'
import api, { ApiError } from '@/lib/api'
import { addDays, formatDate, formatHours, startOfWeek, toISODate } from '@/lib/utils'

import { PageHeader } from '@/components/PageHeader'
import { SessionCard } from '@/components/SessionCard'
import { GeneratedPlan } from '@/components/planner/GeneratedPlan'
import { PlanBuildingPanel } from '@/components/planner/PlanBuildingPanel'
import { Badge } from '@/components/ui/badge'
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
import { SkeletonList } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

const KINDS = ['study', 'revision', 'admission', 'past_paper', 'break']

const EMPTY_SESSION = {
  title: '',
  subject_id: '',
  session_date: toISODate(new Date()),
  start_time: '17:00',
  duration_minutes: 60,
  kind: 'study',
}

export default function StudyPlanner() {
  const { toast } = useToast()
  const { startTimer, refresh: refreshReminders } = useStudySession()
  const [searchParams, setSearchParams] = useSearchParams()
  const [weekStart, setWeekStart] = useState(() => toISODate(startOfWeek(new Date())))
  const [dialogOpen, setDialogOpen] = useState(false)
  const [form, setForm] = useState(EMPTY_SESSION)
  const [genPending, wrapGen] = usePending()
  const [formPending, wrapForm] = usePending()
  //: The plan returned by the last generation, shown in full below the header.
  const [plan, setPlan] = useState(null)
  const [tab, setTab] = useState('today')
  const resultRef = useRef(null)

  /*
   * Generation takes about 80ms against a warm local server and tens of seconds
   * against a sleeping free-tier one. Showing the progress panel immediately
   * would make the fast case flicker, so it only appears once the request has
   * been running long enough to be worth explaining.
   */
  const [showProgress, setShowProgress] = useState(false)
  useEffect(() => {
    if (!genPending) {
      setShowProgress(false)
      return undefined
    }
    const timer = setTimeout(() => setShowProgress(true), 250)
    return () => clearTimeout(timer)
  }, [genPending])

  const { data: subjects } = useFetch(() => api.subjects.list(), [])
  const {
    data: today,
    loading: todayLoading,
    reload: reloadToday,
  } = useFetch(() => api.plans.today(), [])
  const {
    data: week,
    loading: weekLoading,
    reload: reloadWeek,
  } = useFetch(() => api.plans.week(weekStart), [weekStart])

  // `refreshReminders` keeps the reminder/timer layer in step with edits made
  // here, so a session added now still gets its two popups.
  const refreshAll = () =>
    Promise.all([
      reloadToday({ silent: true }),
      reloadWeek({ silent: true }),
      refreshReminders(),
    ])

  const act = async (session, action) => {
    try {
      if (action === 'complete') await api.plans.completeSession(session.id)
      if (action === 'skip') await api.plans.skipSession(session.id)
      if (action === 'reset') await api.plans.resetSession(session.id)
      if (action === 'delete') await api.plans.removeSession(session.id)
      await refreshAll()
    } catch (err) {
      toast.error('Could not update session', err instanceof ApiError ? err.message : undefined)
    }
  }

  const generate = useCallback(
    () =>
      wrapGen(async () => {
        setPlan(null)
        // Scroll to the panel that has just replaced the plan area, so the
        // progress is visible immediately rather than only the button spinner.
        requestAnimationFrame(() =>
          resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }),
        )
        try {
          const generated = await api.plans.generate({})
          setPlan(generated)
          await refreshAll()
          // Scroll again once the real output has laid out, since it is much
          // taller than the progress panel it replaced.
          requestAnimationFrame(() =>
            resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }),
          )
          toast.success(
            'Plan ready',
            `${generated.sessions?.length ?? 0} sessions across ${generated.horizon_days} days`,
          )
        } catch (err) {
          toast.error(
            'Could not generate a plan',
            err instanceof ApiError ? err.message : undefined,
          )
        }
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [wrapGen],
  )

  // The dashboard's generate button links here with ?generate=1 so the output
  // always appears on the page built to show it.
  useEffect(() => {
    if (searchParams.get('generate') !== '1') return
    setSearchParams({}, { replace: true })
    generate()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const submitSession = () =>
    wrapForm(async () => {
      try {
        await api.plans.createSession({
          title: form.title.trim(),
          subject_id: form.subject_id ? Number(form.subject_id) : null,
          session_date: form.session_date,
          start_time: form.start_time,
          duration_minutes: Number(form.duration_minutes),
          kind: form.kind,
        })
        setDialogOpen(false)
        setForm(EMPTY_SESSION)
        await refreshAll()
        toast.success('Session added')
      } catch (err) {
        toast.error('Could not add session', err instanceof ApiError ? err.message : undefined)
      }
    })

  return (
    <div className="space-y-6">
      <PageHeader
        title="Study Planner"
        description="Your timetable for today, this week and the month ahead."
        icon={CalendarClock}
        actions={
          <>
            <Button loading={genPending} onClick={generate}>
              <CalendarPlus /> Generate new plan
            </Button>
            <Button variant="subtle" onClick={() => setDialogOpen(true)}>
              <Plus /> Add session
            </Button>
          </>
        }
      />

      {/* Scroll target for a generation: the progress panel and then the plan
          itself both land here, directly under the button that started it. */}
      <div ref={resultRef} className="scroll-mt-20">
        {showProgress ? (
          <PlanBuildingPanel />
        ) : (
          !genPending && plan && <GeneratedPlan plan={plan} onOpenWeek={() => setTab('week')} />
        )}
      </div>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="today">Today</TabsTrigger>
          <TabsTrigger value="week">This Week</TabsTrigger>
        </TabsList>

        <TabsContent value="today" className="space-y-3">
          {todayLoading ? (
            <SkeletonList rows={3} />
          ) : today?.length ? (
            today.map((session, index) => (
              <SessionCard
                key={session.id}
                session={session}
                index={index}
                onStart={startTimer}
                onComplete={(s) => act(s, 'complete')}
                onSkip={(s) => act(s, 'skip')}
                onReset={(s) => act(s, 'reset')}
                onDelete={(s) => act(s, 'delete')}
              />
            ))
          ) : (
            <EmptyState
              icon={CalendarClock}
              title="Nothing scheduled today"
              description="Generate a plan, or add a session yourself."
              action={
                <Button onClick={generate} loading={genPending}>
                  <CalendarPlus /> Generate a plan
                </Button>
              }
            />
          )}
        </TabsContent>

        <TabsContent value="week">
          <div className="mb-4 flex items-center justify-between">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setWeekStart(toISODate(addDays(weekStart, -7)))}
            >
              <ChevronLeft /> Previous
            </Button>
            <div className="text-center">
              <p className="text-sm font-semibold">
                {week ? `${formatDate(week.week_start)} to ${formatDate(week.week_end)}` : '-'}
              </p>
              {week && (
                <p className="text-xs text-muted-foreground">
                  {formatHours(week.completed_hours)} / {formatHours(week.total_hours)} completed
                </p>
              )}
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setWeekStart(toISODate(addDays(weekStart, 7)))}
            >
              Next <ChevronRight />
            </Button>
          </div>

          {weekLoading ? (
            <SkeletonList rows={4} />
          ) : (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              {week?.days.map((day) => (
                <Card key={day.date}>
                  <CardHeader className="pb-2">
                    <CardTitle className="flex items-center justify-between text-sm">
                      {day.label}
                      <Badge variant="outline">{formatDate(day.date)}</Badge>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2 pt-0">
                    {day.sessions.length === 0 ? (
                      <p className="py-3 text-center text-xs text-muted-foreground">Free day</p>
                    ) : (
                      day.sessions.map((session, index) => (
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
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add a study session</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <Field label="Title" required>
              <Input
                value={form.title}
                onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
                placeholder="e.g. Algebra revision"
              />
            </Field>
            <div className="grid grid-cols-2 gap-3">
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
              <Field label="Kind">
                <Select
                  value={form.kind}
                  onValueChange={(v) => setForm((f) => ({ ...f, kind: v }))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {KINDS.map((k) => (
                      <SelectItem key={k} value={k}>
                        {k.replace('_', ' ')}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <Field label="Date">
                <Input
                  type="date"
                  value={form.session_date}
                  onChange={(e) => setForm((f) => ({ ...f, session_date: e.target.value }))}
                />
              </Field>
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
            <Button onClick={submitSession} loading={formPending} disabled={!form.title.trim()}>
              Add session
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
