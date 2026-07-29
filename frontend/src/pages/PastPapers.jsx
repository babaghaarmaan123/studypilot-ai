import { useState } from 'react'
import { Award, FileText, Hourglass, Plus, Target, TrendingUp } from 'lucide-react'

import { useToast } from '@/context/ToastContext'
import { useFetch, usePending } from '@/hooks/useFetch'
import api, { ApiError } from '@/lib/api'
import { toISODate } from '@/lib/utils'

import { PageHeader } from '@/components/PageHeader'
import { StatCard } from '@/components/StatCard'
import { ConfirmDialog } from '@/components/ConfirmDialog'
import { AreaChart } from '@/components/charts/Charts'
import { PaperRow } from '@/components/pastpapers/PaperRow'
import { PaperUploadCard } from '@/components/pastpapers/PaperUploadCard'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
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
import { SkeletonList, SkeletonStats } from '@/components/ui/skeleton'

const EMPTY_FORM = {
  subject_id: '',
  title: '',
  exam_board: '',
  year: '',
  paper: '',
  session_label: '',
  date_taken: toISODate(new Date()),
  marks_scored: '',
  marks_total: '',
  time_taken_minutes: '',
  under_timed_conditions: true,
  notes: '',
}

export default function PastPapers() {
  const { toast } = useToast()
  const { data: subjects } = useFetch(() => api.subjects.list(), [])
  const { data: papers, loading, reload, setData } = useFetch(() => api.pastPapers.list(), [])
  const { data: stats, reload: reloadStats } = useFetch(() => api.pastPapers.stats(), [])
  const [pending, wrap] = usePending()
  const [uploading, setUploading] = useState(false)

  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState(EMPTY_FORM)
  const [deleteTarget, setDeleteTarget] = useState(null)

  const refreshAll = () => Promise.all([reload({ silent: true }), reloadStats({ silent: true })])

  const openCreate = () => {
    setEditing(null)
    setForm(EMPTY_FORM)
    setDialogOpen(true)
  }

  const openEdit = (paper) => {
    setEditing(paper)
    setForm({
      subject_id: String(paper.subject_id),
      title: paper.title,
      exam_board: paper.exam_board || '',
      year: paper.year || '',
      paper: paper.paper || '',
      session_label: paper.session_label || '',
      date_taken: paper.date_taken,
      marks_scored: paper.scored ? paper.marks_scored : '',
      marks_total: paper.marks_total,
      time_taken_minutes: paper.time_taken_minutes || '',
      under_timed_conditions: paper.under_timed_conditions,
      notes: paper.notes || '',
    })
    setDialogOpen(true)
  }

  /** Uploads each dropped PDF; the backend reads the cover page for metadata. */
  const upload = async (files, subjectId) => {
    setUploading(true)
    let added = 0
    try {
      for (const file of files) {
        try {
          await api.pastPapers.upload(file, { subject_id: subjectId })
          added += 1
        } catch (err) {
          toast.error(
            `Could not upload ${file.name}`,
            err instanceof ApiError ? err.message : undefined,
          )
        }
      }
      if (added) {
        await refreshAll()
        toast.success(
          added === 1 ? 'Paper uploaded' : `${added} papers uploaded`,
          'Add your marks below once it is marked.',
        )
      }
    } finally {
      setUploading(false)
    }
  }

  const saveScore = (paper, body) =>
    wrap(async () => {
      try {
        await api.pastPapers.score(paper.id, body)
        await refreshAll()
        toast.success('Score saved')
      } catch (err) {
        toast.error('Could not save that score', err instanceof ApiError ? err.message : undefined)
      }
    })

  const submit = () =>
    wrap(async () => {
      try {
        const payload = {
          title: form.title.trim(),
          exam_board: form.exam_board || null,
          year: form.year ? Number(form.year) : null,
          paper: form.paper || null,
          session_label: form.session_label || null,
          date_taken: form.date_taken,
          marks_scored: Number(form.marks_scored),
          marks_total: Number(form.marks_total),
          time_taken_minutes: form.time_taken_minutes ? Number(form.time_taken_minutes) : null,
          under_timed_conditions: form.under_timed_conditions,
          notes: form.notes || null,
        }
        if (editing) {
          await api.pastPapers.update(editing.id, payload)
        } else {
          await api.pastPapers.create({ ...payload, subject_id: Number(form.subject_id) })
        }
        setDialogOpen(false)
        await refreshAll()
        toast.success(editing ? 'Past paper updated' : 'Past paper logged')
      } catch (err) {
        toast.error('Could not save that paper', err instanceof ApiError ? err.message : undefined)
      }
    })

  const confirmDelete = () =>
    wrap(async () => {
      try {
        await api.pastPapers.remove(deleteTarget.id)
        setData((current) => current.filter((p) => p.id !== deleteTarget.id))
        setDeleteTarget(null)
        reloadStats({ silent: true })
      } catch (err) {
        toast.error('Could not delete', err instanceof ApiError ? err.message : undefined)
      }
    })

  const trend = stats?.trend || []
  const awaiting = stats?.awaiting_score || 0

  return (
    <div className="space-y-8">
      <PageHeader
        title="Past Papers"
        description="Upload each paper you sit and watch your scores climb."
        icon={FileText}
        actions={
          <Button variant="outline" onClick={openCreate} disabled={!subjects?.length}>
            <Plus /> Add without a PDF
          </Button>
        }
      />

      <PaperUploadCard subjects={subjects} uploading={uploading} onUpload={upload} />

      {!stats ? (
        <SkeletonStats count={4} />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {awaiting > 0 ? (
            <StatCard label="Awaiting score" value={awaiting} icon={Hourglass} tone="amber" />
          ) : (
            <StatCard
              label="Papers marked"
              value={stats.total_papers}
              icon={FileText}
              tone="indigo"
            />
          )}
          <StatCard
            label="Average score"
            value={`${stats.average_percentage}%`}
            icon={Target}
            tone="sky"
          />
          <StatCard
            label="Best score"
            value={`${stats.best_percentage}%`}
            icon={Award}
            tone="amber"
          />
          <StatCard
            label="Improvement"
            value={`${stats.improvement > 0 ? '+' : ''}${stats.improvement}%`}
            trend={stats.improvement}
            icon={TrendingUp}
            tone="emerald"
          />
        </div>
      )}

      {trend.length > 1 && (
        <Card>
          <CardHeader>
            <CardTitle>Improvement over time</CardTitle>
          </CardHeader>
          <CardContent>
            <AreaChart
              labels={trend.map((t) => t.label)}
              values={trend.map((t) => t.percentage)}
              label="Score"
              suffix="%"
              colour="#6366f1"
            />
          </CardContent>
        </Card>
      )}

      {stats?.by_subject?.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>By subject</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {stats.by_subject.map((s) => (
                <div
                  key={s.subject_id}
                  className="rounded-2xl border border-border/70 p-4"
                  style={{ borderLeftColor: s.colour, borderLeftWidth: 4 }}
                >
                  <p className="text-sm font-semibold">{s.name}</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {s.count} papers · avg {s.average}% · best {s.best}%
                  </p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Your papers</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2.5">
          {loading ? (
            <SkeletonList rows={4} />
          ) : papers?.length ? (
            papers.map((paper) => (
              <PaperRow
                key={paper.id}
                paper={paper}
                pending={pending}
                onScore={saveScore}
                onEdit={openEdit}
                onDelete={setDeleteTarget}
              />
            ))
          ) : (
            <EmptyState
              icon={FileText}
              title="No past papers yet"
              description={
                subjects?.length
                  ? 'Upload a paper above to start tracking your improvement.'
                  : 'Add a subject first, then upload your papers here.'
              }
            />
          )}
        </CardContent>
      </Card>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{editing ? 'Edit past paper' : 'Log a past paper'}</DialogTitle>
          </DialogHeader>
          <div className="max-h-[65vh] space-y-4 overflow-y-auto pr-1">
            {!editing && (
              <Field label="Subject" required>
                <Select
                  value={form.subject_id}
                  onValueChange={(v) => setForm((f) => ({ ...f, subject_id: v }))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select subject" />
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
            )}

            <Field label="Title" required>
              <Input
                value={form.title}
                onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
                placeholder="e.g. Paper 1: Pure Mathematics"
              />
            </Field>

            <div className="grid grid-cols-3 gap-3">
              <Field label="Exam board">
                <Input
                  value={form.exam_board}
                  onChange={(e) => setForm((f) => ({ ...f, exam_board: e.target.value }))}
                />
              </Field>
              <Field label="Year">
                <Input
                  type="number"
                  value={form.year}
                  onChange={(e) => setForm((f) => ({ ...f, year: e.target.value }))}
                />
              </Field>
              <Field label="Paper">
                <Input
                  value={form.paper}
                  onChange={(e) => setForm((f) => ({ ...f, paper: e.target.value }))}
                  placeholder="Paper 1"
                />
              </Field>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <Field label="Date taken" required>
                <Input
                  type="date"
                  value={form.date_taken}
                  onChange={(e) => setForm((f) => ({ ...f, date_taken: e.target.value }))}
                />
              </Field>
              <Field label="Session">
                <Input
                  value={form.session_label}
                  onChange={(e) => setForm((f) => ({ ...f, session_label: e.target.value }))}
                  placeholder="e.g. Mock 2"
                />
              </Field>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <Field label="Marks scored" required>
                <Input
                  type="number"
                  min={0}
                  value={form.marks_scored}
                  onChange={(e) => setForm((f) => ({ ...f, marks_scored: e.target.value }))}
                />
              </Field>
              <Field label="Marks total" required>
                <Input
                  type="number"
                  min={1}
                  value={form.marks_total}
                  onChange={(e) => setForm((f) => ({ ...f, marks_total: e.target.value }))}
                />
              </Field>
              <Field label="Time (min)">
                <Input
                  type="number"
                  min={0}
                  value={form.time_taken_minutes}
                  onChange={(e) => setForm((f) => ({ ...f, time_taken_minutes: e.target.value }))}
                />
              </Field>
            </div>

            <label className="flex items-center gap-2 text-sm">
              <Checkbox
                checked={form.under_timed_conditions}
                onCheckedChange={(v) =>
                  setForm((f) => ({ ...f, under_timed_conditions: Boolean(v) }))
                }
              />
              Sat under timed conditions
            </label>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={submit}
              loading={pending}
              disabled={
                !form.title.trim() ||
                !form.marks_scored ||
                !form.marks_total ||
                (!editing && !form.subject_id)
              }
            >
              {editing ? 'Save changes' : 'Log paper'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title={`Delete "${deleteTarget?.title}"?`}
        description="This removes the paper and its PDF. This cannot be undone."
        confirmLabel="Delete"
        loading={pending}
        onConfirm={confirmDelete}
      />
    </div>
  )
}
