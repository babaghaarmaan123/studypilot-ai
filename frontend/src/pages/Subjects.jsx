import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Archive,
  ArchiveRestore,
  BookOpen,
  FileUp,
  MoreVertical,
  Pencil,
  Plus,
  Trash2,
} from 'lucide-react'

import { useAuth } from '@/context/AuthContext'
import { useToast } from '@/context/ToastContext'
import { useFetch, usePending } from '@/hooks/useFetch'
import api, { ApiError } from '@/lib/api'
import {
  CURRICULUM_LABELS,
  DIFFICULTY_LABELS,
  SYLLABUS_STATUS_META,
  cn,
  colourForSubject,
  formatHours,
  hexToRgba,
} from '@/lib/utils'

import { PageHeader } from '@/components/PageHeader'
import { ConfirmDialog } from '@/components/ConfirmDialog'
import { SubjectPickerModal } from '@/components/subjects/SubjectPickerModal'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { EmptyState } from '@/components/ui/empty-state'
import { Field } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { ProgressRing } from '@/components/ui/progress'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { SkeletonList } from '@/components/ui/skeleton'

const PRIORITIES = ['low', 'medium', 'high']

const EMPTY_EDIT_FORM = {
  name: '',
  exam_board: '',
  colour: '#6366f1',
  difficulty: 3,
  priority: 'medium',
  estimated_hours: 40,
  target_grade: '',
  confidence: 3,
}

/** One subject's card — compact, information-dense, premium-SaaS styled. */
function SubjectCard({ subject, onEdit, onArchive, onDelete, onUploadPdf, uploading }) {
  const fileRef = useRef(null)
  const navigate = useNavigate()
  const statusMeta = SYLLABUS_STATUS_META[subject.syllabus_status] || SYLLABUS_STATUS_META.not_uploaded
  const busy = uploading === subject.id

  return (
    <Card className="card-hover flex flex-col overflow-hidden">
      <input
        ref={fileRef}
        type="file"
        accept="application/pdf"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (file) onUploadPdf(subject, file)
          e.target.value = ''
        }}
      />
      <CardContent className="flex flex-1 flex-col p-4">
        <div className="flex items-start justify-between gap-2">
          <div className="flex min-w-0 items-center gap-2.5">
            <span
              className="grid size-9 shrink-0 place-items-center rounded-xl text-sm font-bold"
              style={{
                backgroundColor: hexToRgba(subject.colour, 0.15),
                color: subject.colour,
              }}
            >
              <BookOpen className="size-4.5" />
            </span>
            <div className="min-w-0">
              <h3 className="truncate font-display text-sm font-semibold leading-tight">
                {subject.name}
              </h3>
              <p className="truncate text-[11px] text-muted-foreground">
                {CURRICULUM_LABELS[subject.curriculum] || 'No curriculum'}
                {subject.exam_board ? ` · ${subject.exam_board}` : ''}
              </p>
            </div>
          </div>

          <div className="flex shrink-0 items-center gap-1.5">
            <ProgressRing value={subject.completion_percentage} size={38} stroke={4} colour={subject.colour} />
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon-sm" aria-label="Subject actions">
                  <MoreVertical />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onSelect={() => onEdit(subject)}>
                  <Pencil /> Edit
                </DropdownMenuItem>
                <DropdownMenuItem onSelect={() => onArchive(subject)}>
                  {subject.is_archived ? <ArchiveRestore /> : <Archive />}
                  {subject.is_archived ? 'Unarchive' : 'Archive'}
                </DropdownMenuItem>
                <DropdownMenuItem destructive onSelect={() => onDelete(subject)}>
                  <Trash2 /> Delete
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-1.5">
          <Badge variant="outline">{DIFFICULTY_LABELS[subject.difficulty]}</Badge>
          <Badge variant={subject.priority === 'high' ? 'destructive' : 'secondary'}>
            {subject.priority} priority
          </Badge>
          {subject.is_weak && <Badge variant="warning">Weak area</Badge>}
        </div>

        <div className="mt-2.5 flex items-center gap-1.5 text-xs text-muted-foreground">
          <span className={cn('size-2 rounded-full', statusMeta.dot)} />
          {statusMeta.label}
        </div>

        <div className="mt-3 grid grid-cols-3 gap-2 rounded-xl bg-muted/40 p-2.5 text-center">
          <div>
            <p className="font-display text-sm font-bold">{subject.completed_topic_count}</p>
            <p className="text-[10px] text-muted-foreground">Done</p>
          </div>
          <div>
            <p className="font-display text-sm font-bold">
              {Math.max(subject.topic_count - subject.completed_topic_count, 0)}
            </p>
            <p className="text-[10px] text-muted-foreground">Remaining</p>
          </div>
          <div>
            <p className="font-display text-sm font-bold">{formatHours(subject.hours_remaining)}</p>
            <p className="text-[10px] text-muted-foreground">Hours left</p>
          </div>
        </div>

        <div className="mt-3 flex gap-2">
          <Button size="sm" className="flex-1" onClick={() => navigate(`/subjects/${subject.id}`)}>
            Open subject
          </Button>
          <Button
            size="sm"
            variant="outline"
            loading={busy}
            onClick={() => fileRef.current?.click()}
            title={subject.syllabus_status === 'not_uploaded' ? 'Upload PDF' : 'Replace PDF'}
          >
            <FileUp />
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

export default function Subjects() {
  const { user } = useAuth()
  const { toast } = useToast()
  const { data: subjects, loading, error, reload, setData } = useFetch(
    () => api.subjects.list(),
    [],
  )
  const { data: catalog } = useFetch(() => api.catalog.all(), [])
  const [pending, wrap] = usePending()
  const [uploadingId, setUploadingId] = useState(null)

  const [pickerOpen, setPickerOpen] = useState(false)
  const [pickerCurriculum, setPickerCurriculum] = useState('')
  const [editing, setEditing] = useState(null)
  const [editForm, setEditForm] = useState(EMPTY_EDIT_FORM)
  const [deleteTarget, setDeleteTarget] = useState(null)

  useEffect(() => {
    if (!pickerCurriculum && (user?.curriculum || catalog?.curricula?.length)) {
      setPickerCurriculum(user?.curriculum || catalog.curricula[0].code)
    }
  }, [user, catalog, pickerCurriculum])

  useEffect(() => {
    if (editing) {
      setEditForm({
        name: editing.name,
        exam_board: editing.exam_board || '',
        colour: editing.colour,
        difficulty: editing.difficulty,
        priority: editing.priority,
        estimated_hours: editing.estimated_hours,
        target_grade: editing.target_grade || '',
        confidence: editing.confidence,
      })
    }
  }, [editing])

  const addSubjects = (names) =>
    wrap(async () => {
      try {
        for (const [index, name] of names.entries()) {
          // Sequential on purpose: each subject's colour depends on how many
          // already exist, so they must be created in order.
          await api.subjects.create({
            name,
            curriculum: pickerCurriculum || null,
            colour: colourForSubject(name, (subjects?.length || 0) + index),
            seed_syllabus: false,
          })
        }
        toast.success(`Added ${names.length} subject${names.length === 1 ? '' : 's'}`)
        setPickerOpen(false)
        reload()
      } catch (err) {
        toast.error('Could not add all subjects', err instanceof ApiError ? err.message : undefined)
      }
    })

  const submitEdit = () =>
    wrap(async () => {
      try {
        const updated = await api.subjects.update(editing.id, {
          name: editForm.name,
          exam_board: editForm.exam_board || null,
          colour: editForm.colour,
          difficulty: Number(editForm.difficulty),
          priority: editForm.priority,
          estimated_hours: Number(editForm.estimated_hours),
          target_grade: editForm.target_grade || null,
          confidence: Number(editForm.confidence),
        })
        setData((current) => current.map((s) => (s.id === updated.id ? updated : s)))
        toast.success('Subject updated')
        setEditing(null)
      } catch (err) {
        toast.error('Could not update subject', err instanceof ApiError ? err.message : undefined)
      }
    })

  const toggleArchive = async (subject) => {
    try {
      const updated = await api.subjects.update(subject.id, { is_archived: !subject.is_archived })
      setData((current) => current.map((s) => (s.id === updated.id ? updated : s)))
      toast.success(updated.is_archived ? 'Subject archived' : 'Subject unarchived')
    } catch (err) {
      toast.error('Could not update subject', err instanceof ApiError ? err.message : undefined)
    }
  }

  const confirmDelete = () =>
    wrap(async () => {
      try {
        await api.subjects.remove(deleteTarget.id)
        setData((current) => current.filter((s) => s.id !== deleteTarget.id))
        toast.success(`${deleteTarget.name} deleted`)
        setDeleteTarget(null)
      } catch (err) {
        toast.error('Could not delete subject', err instanceof ApiError ? err.message : undefined)
      }
    })

  const uploadPdf = async (subject, file) => {
    setUploadingId(subject.id)
    try {
      const updated = await api.subjects.uploadSyllabusPdf(subject.id, file)
      setData((current) => current.map((s) => (s.id === updated.id ? updated : s)))
      toast.success(`Syllabus generated for ${subject.name}`)
    } catch (err) {
      toast.error('Could not process that PDF', err instanceof ApiError ? err.message : undefined)
    } finally {
      setUploadingId(null)
    }
  }

  const examBoards = catalog?.exam_boards?.[editing?.curriculum] || []
  const visibleSubjects = (subjects || []).filter((s) => !s.is_archived)

  return (
    <div className="space-y-6">
      <PageHeader
        title="Subjects"
        description="Add every subject you're studying, then upload its official specification to build the syllabus."
        icon={BookOpen}
        actions={
          <Button onClick={() => setPickerOpen(true)}>
            <Plus /> Add subjects
          </Button>
        }
      />

      {loading ? (
        <SkeletonList rows={4} />
      ) : error ? (
        <EmptyState icon={BookOpen} title="Couldn't load subjects" description={error.message} />
      ) : visibleSubjects.length ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {visibleSubjects.map((subject) => (
            <SubjectCard
              key={subject.id}
              subject={subject}
              onEdit={setEditing}
              onArchive={toggleArchive}
              onDelete={setDeleteTarget}
              onUploadPdf={uploadPdf}
              uploading={uploadingId}
            />
          ))}
        </div>
      ) : (
        <EmptyState
          icon={BookOpen}
          title="Let's build your study plan."
          description="You haven't added any subjects yet."
          action={
            <Button onClick={() => setPickerOpen(true)}>
              <Plus /> Add your first subject
            </Button>
          }
        />
      )}

      <SubjectPickerModal
        open={pickerOpen}
        onOpenChange={setPickerOpen}
        options={catalog?.subjects?.[pickerCurriculum] || []}
        existingNames={(subjects || []).map((s) => s.name)}
        onSubmit={addSubjects}
        loading={pending}
      />

      <Dialog open={Boolean(editing)} onOpenChange={(open) => !open && setEditing(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit subject</DialogTitle>
          </DialogHeader>

          <div className="space-y-4">
            <Field label="Subject name" required>
              <Input
                value={editForm.name}
                onChange={(e) => setEditForm((f) => ({ ...f, name: e.target.value }))}
              />
            </Field>

            <div className="grid grid-cols-2 gap-3">
              <Field label="Exam board">
                <Select
                  value={editForm.exam_board || undefined}
                  onValueChange={(v) => setEditForm((f) => ({ ...f, exam_board: v }))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Optional" />
                  </SelectTrigger>
                  <SelectContent>
                    {examBoards.map((board) => (
                      <SelectItem key={board} value={board}>
                        {board}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>
              <Field label="Priority">
                <Select
                  value={editForm.priority}
                  onValueChange={(v) => setEditForm((f) => ({ ...f, priority: v }))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {PRIORITIES.map((p) => (
                      <SelectItem key={p} value={p}>
                        {p[0].toUpperCase() + p.slice(1)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <Field label="Difficulty (1–5)">
                <Input
                  type="number"
                  min={1}
                  max={5}
                  value={editForm.difficulty}
                  onChange={(e) => setEditForm((f) => ({ ...f, difficulty: e.target.value }))}
                />
              </Field>
              <Field label="Confidence (1–5)">
                <Input
                  type="number"
                  min={1}
                  max={5}
                  value={editForm.confidence}
                  onChange={(e) => setEditForm((f) => ({ ...f, confidence: e.target.value }))}
                />
              </Field>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <Field label="Estimated hours">
                <Input
                  type="number"
                  min={1}
                  max={1000}
                  value={editForm.estimated_hours}
                  onChange={(e) => setEditForm((f) => ({ ...f, estimated_hours: e.target.value }))}
                />
              </Field>
              <Field label="Target grade" hint="Optional">
                <Input
                  value={editForm.target_grade}
                  onChange={(e) => setEditForm((f) => ({ ...f, target_grade: e.target.value }))}
                  placeholder="e.g. A*"
                />
              </Field>
            </div>

            <Field label="Colour">
              <div className="flex flex-wrap gap-2">
                {(catalog?.subject_colours || []).map((colour) => (
                  <button
                    key={colour}
                    type="button"
                    onClick={() => setEditForm((f) => ({ ...f, colour }))}
                    aria-label={`Choose colour ${colour}`}
                    className={cn(
                      'size-8 rounded-full border-2 transition-transform hover:scale-110',
                      editForm.colour === colour ? 'border-foreground' : 'border-transparent',
                    )}
                    style={{ backgroundColor: colour }}
                  />
                ))}
              </div>
            </Field>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setEditing(null)}>
              Cancel
            </Button>
            <Button onClick={submitEdit} loading={pending} disabled={!editForm.name.trim()}>
              Save changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title={`Delete ${deleteTarget?.name}?`}
        description="This removes the subject, its syllabus and every linked session. This cannot be undone."
        confirmLabel="Delete subject"
        loading={pending}
        onConfirm={confirmDelete}
      />
    </div>
  )
}
