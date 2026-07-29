import {
  Award,
  BarChart3,
  Clock,
  Flame,
  Target,
  TrendingUp,
} from 'lucide-react'

import { useFetch } from '@/hooks/useFetch'
import api from '@/lib/api'
import { formatHours, pluralise } from '@/lib/utils'

import { PageHeader } from '@/components/PageHeader'
import { StatCard } from '@/components/StatCard'
import { AreaChart, ColumnChart, DonutChart, RadarChart } from '@/components/charts/Charts'
import { StudyHeatmap } from '@/components/charts/Heatmap'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { EmptyState } from '@/components/ui/empty-state'
import { Progress } from '@/components/ui/progress'
import { SkeletonCard, SkeletonStats } from '@/components/ui/skeleton'

export default function Analytics() {
  const { data, loading, error } = useFetch(() => api.analytics(), [])

  if (error) {
    return (
      <EmptyState
        icon={BarChart3}
        title="Couldn't load analytics"
        description={error.message}
      />
    )
  }

  const totals = data?.totals

  return (
    <div className="space-y-8">
      <PageHeader
        title="Analytics"
        description="Your study patterns, exam readiness and revision progress at a glance."
        icon={BarChart3}
      />

      {loading || !totals ? (
        <SkeletonStats />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Total study time" value={formatHours(totals.total_hours)} icon={Clock} tone="indigo" />
          <StatCard
            label="Overall completion"
            value={`${totals.overall_completion}%`}
            progress={totals.overall_completion}
            icon={TrendingUp}
            tone="emerald"
          />
          <StatCard
            label="Plan adherence"
            value={`${totals.adherence}%`}
            progress={totals.adherence}
            hint={`${Math.round(totals.sessions_completed)} completed · ${Math.round(totals.sessions_missed)} missed`}
            icon={Target}
            tone="sky"
          />
          <StatCard
            label="Streak"
            value={pluralise(Math.round(totals.streak_current), 'day')}
            hint={`Best: ${pluralise(Math.round(totals.streak_longest), 'day')} · ${Math.round(totals.xp)} XP`}
            icon={Flame}
            tone="amber"
          />
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>This week's hours</CardTitle>
          </CardHeader>
          <CardContent>
            {loading || !data ? (
              <SkeletonCard />
            ) : (
              <ColumnChart
                labels={data.weekly_hours.map((d) => d.label)}
                values={data.weekly_hours.map((d) => d.value)}
              />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Last 12 weeks</CardTitle>
          </CardHeader>
          <CardContent>
            {loading || !data ? (
              <SkeletonCard />
            ) : (
              <AreaChart
                labels={data.monthly_hours.map((d) => d.label)}
                values={data.monthly_hours.map((d) => d.value)}
              />
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Subject distribution (30 days)</CardTitle>
          </CardHeader>
          <CardContent>
            {loading || !data ? (
              <SkeletonCard />
            ) : data.subject_distribution.length ? (
              <DonutChart
                labels={data.subject_distribution.map((s) => s.name)}
                values={data.subject_distribution.map((s) => s.hours)}
                colours={data.subject_distribution.map((s) => s.colour)}
              />
            ) : (
              <EmptyState
                icon={BarChart3}
                title="No study time logged yet"
                description="Complete a few sessions to see your distribution."
                className="py-8"
              />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Completion by subject</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {loading || !data ? (
              <SkeletonCard />
            ) : data.completion_by_subject.length ? (
              data.completion_by_subject.map((s) => (
                <div key={s.subject_id}>
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium">{s.name}</span>
                    <span className="text-muted-foreground">
                      {s.topics_done}/{s.topics_total} · {Math.round(s.completion)}%
                    </span>
                  </div>
                  <Progress value={s.completion} className="mt-1.5" />
                </div>
              ))
            ) : (
              <p className="py-4 text-center text-sm text-muted-foreground">No subjects yet.</p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Study streak (last 12 weeks)</CardTitle>
        </CardHeader>
        <CardContent>
          {loading || !data ? (
            <SkeletonCard />
          ) : (
            <StudyHeatmap days={data.streak_calendar} />
          )}
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Exam readiness</CardTitle>
          </CardHeader>
          <CardContent>
            {loading || !data ? (
              <SkeletonCard />
            ) : data.exam_readiness.length >= 3 ? (
              <RadarChart
                labels={data.exam_readiness.map((e) => e.subject)}
                values={data.exam_readiness.map((e) => e.readiness)}
              />
            ) : data.exam_readiness.length ? (
              <div className="space-y-3">
                {data.exam_readiness.map((e) => (
                  <div key={e.exam_id}>
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-medium">{e.subject}</span>
                      <span className="text-muted-foreground">{Math.round(e.readiness)}%</span>
                    </div>
                    <Progress value={e.readiness} className="mt-1.5" />
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                icon={Target}
                title="No upcoming exams"
                description="Add exam dates to track readiness."
                className="py-8"
              />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Admissions readiness</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {loading || !data ? (
              <SkeletonCard />
            ) : data.admission_readiness.length ? (
              data.admission_readiness.map((a) => (
                <div key={a.code}>
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium">{a.name}</span>
                    <span className="text-muted-foreground">{Math.round(a.readiness)}%</span>
                  </div>
                  <Progress value={a.readiness} className="mt-1.5" />
                </div>
              ))
            ) : (
              <EmptyState
                icon={Award}
                title="No admissions tests"
                description="Add these during onboarding or your profile."
                className="py-8"
              />
            )}
          </CardContent>
        </Card>
      </div>

      {data?.past_paper_trend?.length > 1 && (
        <Card>
          <CardHeader>
            <CardTitle>Past paper improvement</CardTitle>
          </CardHeader>
          <CardContent>
            <AreaChart
              labels={data.past_paper_trend.map((t) => t.label)}
              values={data.past_paper_trend.map((t) => t.percentage)}
              suffix="%"
              colour="#14b8a6"
            />
          </CardContent>
        </Card>
      )}
    </div>
  )
}
