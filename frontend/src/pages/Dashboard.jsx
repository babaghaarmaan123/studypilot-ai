import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  BarChart3,
  BookOpen,
  CalendarDays,
  CalendarPlus,
  ClipboardList,
  Clock,
  Flame,
  LayoutDashboard,
  ListChecks,
  RotateCcw,
  Target,
  TrendingUp,
} from 'lucide-react'

import { useStudySession } from '@/context/StudySessionContext'
import { useToast } from '@/context/ToastContext'
import { useFetch } from '@/hooks/useFetch'
import api, { ApiError } from '@/lib/api'
import { formatMinutes, iconFor, pluralise } from '@/lib/utils'

import { PageHeader } from '@/components/PageHeader'
import { StatCard } from '@/components/StatCard'
import { SessionCard } from '@/components/SessionCard'
import { CountdownCard } from '@/components/CountdownCard'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { EmptyState } from '@/components/ui/empty-state'
import { SkeletonList, SkeletonStats } from '@/components/ui/skeleton'

const QUICK_ACTIONS = [
  { to: '/planner?generate=1', label: 'Generate a plan', icon: CalendarPlus, tone: 'primary' },
  { to: '/revision', label: 'Revision', icon: RotateCcw, tone: 'emerald' },
  { to: '/calendar', label: 'Calendar', icon: CalendarDays, tone: 'sky' },
  { to: '/past-papers', label: 'Past Papers', icon: ClipboardList, tone: 'amber' },
  { to: '/analytics', label: 'Analytics', icon: BarChart3, tone: 'primary' },
]

export default function Dashboard() {
  const { toast } = useToast()
  const navigate = useNavigate()
  const { startTimer } = useStudySession()
  const { data, loading, error, reload } = useFetch(() => api.dashboard(), [])
  const [busySession, setBusySession] = useState(null)

  const updateSession = async (session, action) => {
    setBusySession(session.id)
    try {
      if (action === 'complete') await api.plans.completeSession(session.id)
      if (action === 'skip') await api.plans.skipSession(session.id)
      if (action === 'reset') await api.plans.resetSession(session.id)
      if (action === 'delete') await api.plans.removeSession(session.id)
      await reload({ silent: true })
    } catch (err) {
      toast.error('Could not update that session', err instanceof ApiError ? err.message : undefined)
    } finally {
      setBusySession(null)
    }
  }

  // Generating from here used to leave the student on the dashboard with a
  // toast and no visible plan. The planner is the page built to display it, so
  // the work happens there and the output is on screen when it finishes.
  const generatePlan = () => navigate('/planner?generate=1')

  if (error) {
    return (
      <EmptyState
        icon={Target}
        title="Couldn't load your dashboard"
        description={error.message}
        action={<Button onClick={() => reload()}>Try again</Button>}
      />
    )
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title={loading ? 'Loading…' : data?.greeting}
        description={
          data?.mentor_summary
            ? data.mentor_summary
            : 'Generate a plan and your week fills itself in.'
        }
        icon={LayoutDashboard}
        actions={
          <Button onClick={generatePlan}>
            <CalendarPlus /> Generate a plan
          </Button>
        }
      />

      {loading || !data ? (
        <SkeletonStats />
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
          <StatCard
            label="Study streak"
            value={pluralise(data.streak_current, 'day')}
            hint={`Longest: ${pluralise(data.streak_longest, 'day')}`}
            icon={Flame}
            tone="amber"
            delay={0}
          />
          <StatCard
            label="Today's goal"
            value={`${formatMinutes(data.todays_completed_minutes)} / ${formatMinutes(
              data.todays_goal_minutes,
            )}`}
            progress={data.todays_progress}
            icon={Target}
            tone="primary"
            delay={0.05}
          />
          <StatCard
            label="Hours remaining today"
            value={`${data.hours_remaining_today}h`}
            hint={`${pluralise(data.revisions_due, 'revision due', 'revisions due')}`}
            icon={Clock}
            tone="sky"
            delay={0.1}
          />
          <StatCard
            label="Overall progress"
            value={`${Math.round(data.overall_progress)}%`}
            progress={data.overall_progress}
            hint={`${data.topics_completed}/${data.topics_total} topics complete`}
            icon={TrendingUp}
            tone="emerald"
            delay={0.15}
          />
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <ListChecks className="size-4.5 text-primary" /> Today's tasks
            </CardTitle>
            {data && (
              <Badge variant={data.missed_sessions > 0 ? 'destructive' : 'secondary'}>
                {data.missed_sessions > 0
                  ? `${pluralise(data.missed_sessions, 'missed session')}`
                  : 'On track'}
              </Badge>
            )}
          </CardHeader>
          <CardContent className="space-y-3">
            {loading ? (
              <SkeletonList rows={3} />
            ) : data?.sessions_today?.length ? (
              data.sessions_today.map((session, index) => (
                <div key={session.id} className={busySession === session.id ? 'opacity-60' : ''}>
                  <SessionCard
                    session={session}
                    index={index}
                    onStart={startTimer}
                    onComplete={(s) => updateSession(s, 'complete')}
                    onSkip={(s) => updateSession(s, 'skip')}
                    onReset={(s) => updateSession(s, 'reset')}
                    onDelete={(s) => updateSession(s, 'delete')}
                  />
                </div>
              ))
            ) : (
              <EmptyState
                icon={CalendarPlus}
                title="Nothing scheduled for today"
                description="Generate a plan and StudyPilot will fill your day automatically."
                action={
                  <Button onClick={generatePlan}>
                    <CalendarPlus /> Generate a plan
                  </Button>
                }
              />
            )}
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CalendarDays className="size-4.5 text-primary" /> Upcoming exams
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {loading ? (
                <SkeletonList rows={2} />
              ) : data?.upcoming_exams?.length ? (
                data.upcoming_exams
                  .slice(0, 3)
                  .map((exam) => <CountdownCard key={exam.id} exam={exam} />)
              ) : (
                <p className="py-4 text-center text-sm text-muted-foreground">
                  No upcoming exams yet.
                </p>
              )}
            </CardContent>
          </Card>

          {data?.admission_countdowns?.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Target className="size-4.5 text-primary" /> Admissions countdown
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {data.admission_countdowns.slice(0, 3).map((exam) => (
                  <CountdownCard key={exam.id} exam={exam} />
                ))}
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Quick actions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
              {QUICK_ACTIONS.map(({ to, label, icon: Icon }) => (
                <Link
                  key={to}
                  to={to}
                  className="card-hover flex flex-col items-center gap-2 rounded-2xl border border-border/70 bg-card p-4 text-center"
                >
                  <span className="grid size-10 place-items-center rounded-xl bg-primary/10 text-primary">
                    <Icon className="size-5" />
                  </span>
                  <span className="text-xs font-semibold leading-tight">{label}</span>
                </Link>
              ))}
            </div>

            {data?.weak_subjects?.length > 0 && (
              <div className="mt-6 border-t border-border/60 pt-5">
                <p className="mb-2.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Needs attention
                </p>
                <div className="flex flex-wrap gap-2">
                  {data.weak_subjects.map((s) => (
                    <Badge
                      key={s.id}
                      variant="destructive"
                      className="gap-1.5"
                      style={{ backgroundColor: `${s.colour}22`, color: s.colour }}
                    >
                      <BookOpen className="size-3" />
                      {s.name}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent activity</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <SkeletonList rows={4} />
            ) : data?.recent_activity?.length ? (
              <ol className="space-y-4">
                {data.recent_activity.slice(0, 8).map((item) => {
                  const Icon = iconFor(item.icon)
                  return (
                    <motion.li
                      key={item.id}
                      initial={{ opacity: 0, x: -6 }}
                      animate={{ opacity: 1, x: 0 }}
                      className="flex items-start gap-3"
                    >
                      <span className="mt-0.5 grid size-8 shrink-0 place-items-center rounded-lg bg-primary/10 text-primary">
                        <Icon className="size-4" />
                      </span>
                      <div className="min-w-0">
                        <p className="text-sm leading-snug">{item.message}</p>
                        <p className="text-xs text-muted-foreground">
                          {new Date(item.created_at).toLocaleString('en-GB', {
                            day: 'numeric',
                            month: 'short',
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </p>
                      </div>
                    </motion.li>
                  )
                })}
              </ol>
            ) : (
              <p className="py-4 text-center text-sm text-muted-foreground">
                Nothing logged yet.
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
