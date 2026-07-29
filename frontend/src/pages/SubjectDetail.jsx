import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  Award,
  BookOpen,
  Clock,
  FileText,
  Save,
  Target,
  TrendingUp,
} from 'lucide-react'

import { useToast } from '@/context/ToastContext'
import { useFetch, usePending } from '@/hooks/useFetch'
import api, { ApiError } from '@/lib/api'
import {
  CURRICULUM_LABELS,
  DIFFICULTY_LABELS,
  SYLLABUS_STATUS_META,
  cn,
  formatDate,
  formatHours,
} from '@/lib/utils'

import { StatCard } from '@/components/StatCard'
import { SyllabusTree } from '@/components/subjects/SyllabusTree'
import { SyllabusUploadPanel } from '@/components/subjects/SyllabusUploadPanel'
import { AreaChart } from '@/components/charts/Charts'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { EmptyState } from '@/components/ui/empty-state'
import { ProgressRing } from '@/components/ui/progress'
import { SkeletonCard } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/input'

function OverviewTab({ subject }) {
  const statusMeta = SYLLABUS_STATUS_META[subject.syllabus_status] || SYLLABUS_STATUS_META.not_uploaded
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
        <StatCard
          label="Completion"
          value={`${Math.round(subject.completion_percentage)}%`}
          progress={subject.completion_percentage}
          icon={TrendingUp}
          tone="emerald"
        />
        <StatCard
          label="Topics"
          value={`${subject.completed_topic_count}/${subject.topic_count}`}
          icon={BookOpen}
          tone="indigo"
        />
        <StatCard label="Hours remaining" value={formatHours(subject.hours_remaining)} icon={Clock} tone="sky" />
        <StatCard
          label="Next exam"
          value={subject.next_exam_date ? formatDate(subject.next_exam_date) : 'Not set'}
          icon={Target}
          tone="amber"
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Subject details</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Difficulty</p>
            <p className="mt-1 text-sm font-medium">{DIFFICULTY_LABELS[subject.difficulty]}</p>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Priority</p>
            <p className="mt-1 text-sm font-medium capitalize">{subject.priority}</p>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Target grade</p>
            <p className="mt-1 text-sm font-medium">{subject.target_grade || 'Not set'}</p>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Syllabus</p>
            <p className="mt-1 flex items-center gap-1.5 text-sm font-medium">
              <span className={cn('size-2 rounded-full', statusMeta.dot)} />
              {statusMeta.label}
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function SyllabusTab({ subject, setSubject }) {
  if (subject.syllabus_status !== 'ready' || subject.units.length === 0) {
    return <SyllabusUploadPanel subject={subject} onUploaded={setSubject} />
  }
  return <SyllabusTree subject={subject} setSubject={setSubject} />
}

function ResourcesTab() {
  return (
    <EmptyState
      icon={FileText}
      title="Resources coming soon"
      description="Linked notes, videos and revision resources for this subject will live here."
      className="py-14"
    />
  )
}

function PastPapersTab({ subjectId, subjectName }) {
  const { data: papers, loading } = useFetch(() => api.pastPapers.list(subjectId), [subjectId])
  const scores = (papers || []).map((p) => p.percentage)
  const average = scores.length ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : 0

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {papers?.length ? `${papers.length} papers logged · ${average}% average` : 'No papers logged yet'}
        </p>
        <Button size="sm" variant="outline" asChild>
          <Link to="/past-papers">
            <FileText /> Log a paper
          </Link>
        </Button>
      </div>

      {loading ? (
        <SkeletonCard />
      ) : papers?.length ? (
        <div className="space-y-2.5">
          {papers.map((paper) => (
            <div
              key={paper.id}
              className="flex items-center justify-between rounded-xl border border-border/60 bg-card p-3.5"
            >
              <div>
                <p className="text-sm font-semibold">{paper.title}</p>
                <p className="text-xs text-muted-foreground">
                  {formatDate(paper.date_taken)} · {paper.marks_scored}/{paper.marks_total} marks
                </p>
              </div>
              <div className="text-right">
                <p className="font-display text-lg font-bold text-primary">{paper.percentage}%</p>
                {paper.grade && <Badge variant="success">{paper.grade}</Badge>}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState
          icon={FileText}
          title="No past papers yet"
          description={`Log a ${subjectName} paper to start tracking your improvement.`}
          className="py-10"
        />
      )}
    </div>
  )
}

function NotesTab({ subject, onSaved }) {
  const { toast } = useToast()
  const [value, setValue] = useState(subject.notes || '')
  const [pending, wrap] = usePending()

  const save = () =>
    wrap(async () => {
      try {
        const updated = await api.subjects.update(subject.id, { notes: value })
        onSaved(updated)
        toast.success('Notes saved')
      } catch (err) {
        toast.error('Could not save notes', err instanceof ApiError ? err.message : undefined)
      }
    })

  return (
    <Card>
      <CardContent className="space-y-3 pt-6">
        <Textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Tricky topics, teacher tips, exam quirks."
          className="min-h-[220px]"
        />
        <Button onClick={save} loading={pending}>
          <Save /> Save notes
        </Button>
      </CardContent>
    </Card>
  )
}

function AnalyticsTab({ subject }) {
  const { data: papers } = useFetch(() => api.pastPapers.list(subject.id), [subject.id])
  const trend = (papers || []).slice().reverse()

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
        <StatCard
          label="Completion"
          value={`${Math.round(subject.completion_percentage)}%`}
          progress={subject.completion_percentage}
          icon={TrendingUp}
          tone="emerald"
        />
        <StatCard label="Confidence" value={`${subject.confidence}/5`} icon={Award} tone="violet" />
        <StatCard label="Difficulty" value={DIFFICULTY_LABELS[subject.difficulty]} icon={Target} tone="amber" />
        <StatCard label="Hours remaining" value={formatHours(subject.hours_remaining)} icon={Clock} tone="sky" />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Past paper trend</CardTitle>
        </CardHeader>
        <CardContent>
          {trend.length > 1 ? (
            <AreaChart
              labels={trend.map((p) => formatDate(p.date_taken))}
              values={trend.map((p) => p.percentage)}
              suffix="%"
              colour={subject.colour}
            />
          ) : (
            <p className="py-8 text-center text-sm text-muted-foreground">
              Log at least two past papers to see a trend here.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export default function SubjectDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const {
    data: subject,
    loading,
    error,
    setData: setSubject,
  } = useFetch(() => api.subjects.get(Number(id)), [id])

  useEffect(() => {
    document.title = subject ? `${subject.name} | StudyPilot AI` : 'StudyPilot AI'
  }, [subject])

  if (loading || !subject) {
    if (error) {
      return (
        <EmptyState
          icon={BookOpen}
          title="Couldn't load this subject"
          description={error.message}
          action={
            <Button onClick={() => navigate('/subjects')}>
              <ArrowLeft /> Back to subjects
            </Button>
          }
        />
      )
    }
    return <SkeletonCard />
  }

  return (
    <div className="space-y-6">
      <Link
        to="/subjects"
        className="inline-flex items-center gap-1.5 text-sm font-medium text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" /> Back to subjects
      </Link>

      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <span
            className="grid size-12 place-items-center rounded-2xl text-primary"
            style={{ backgroundColor: `${subject.colour}22`, color: subject.colour }}
          >
            <BookOpen className="size-6" />
          </span>
          <div>
            <h1 className="font-display text-2xl font-bold tracking-tight">{subject.name}</h1>
            <p className="text-sm text-muted-foreground">
              {CURRICULUM_LABELS[subject.curriculum] || 'No curriculum'}
              {subject.exam_board ? ` · ${subject.exam_board}` : ''}
            </p>
          </div>
        </div>
        <ProgressRing value={subject.completion_percentage} size={56} colour={subject.colour} />
      </div>

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="syllabus">Syllabus</TabsTrigger>
          <TabsTrigger value="resources">Resources</TabsTrigger>
          <TabsTrigger value="past-papers">Past Papers</TabsTrigger>
          <TabsTrigger value="notes">Notes</TabsTrigger>
          <TabsTrigger value="analytics">Analytics</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <OverviewTab subject={subject} />
        </TabsContent>
        <TabsContent value="syllabus">
          <SyllabusTab subject={subject} setSubject={setSubject} />
        </TabsContent>
        <TabsContent value="resources">
          <ResourcesTab />
        </TabsContent>
        <TabsContent value="past-papers">
          <PastPapersTab subjectId={subject.id} subjectName={subject.name} />
        </TabsContent>
        <TabsContent value="notes">
          <NotesTab subject={subject} onSaved={setSubject} />
        </TabsContent>
        <TabsContent value="analytics">
          <AnalyticsTab subject={subject} />
        </TabsContent>
      </Tabs>
    </div>
  )
}
