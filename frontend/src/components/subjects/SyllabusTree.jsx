import { useState } from 'react'
import { ChevronDown, ChevronRight, Plus, Trash2 } from 'lucide-react'

import { useToast } from '@/context/ToastContext'
import { usePending } from '@/hooks/useFetch'
import api, { ApiError } from '@/lib/api'
import { DIFFICULTY_LABELS, cn } from '@/lib/utils'

import { ConfirmDialog } from '@/components/ConfirmDialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Progress } from '@/components/ui/progress'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

function AddUnitForm({ subjectId, onAdded }) {
  const [name, setName] = useState('')
  const [pending, wrap] = usePending()
  const { toast } = useToast()

  const submit = async (event) => {
    event.preventDefault()
    if (!name.trim()) return
    await wrap(async () => {
      try {
        const unit = await api.subjects.createUnit(subjectId, { name: name.trim() })
        onAdded(unit)
        setName('')
      } catch (err) {
        toast.error('Could not add unit', err instanceof ApiError ? err.message : undefined)
      }
    })
  }

  return (
    <form onSubmit={submit} className="flex gap-2">
      <Input
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="New unit name, e.g. Organic Chemistry"
      />
      <Button type="submit" loading={pending} disabled={!name.trim()}>
        <Plus /> Add unit
      </Button>
    </form>
  )
}

function AddTopicForm({ unitId, onAdded, onCancel }) {
  const [form, setForm] = useState({ name: '', estimated_hours: 2, difficulty: 3 })
  const [pending, wrap] = usePending()
  const { toast } = useToast()

  const submit = async (event) => {
    event.preventDefault()
    if (!form.name.trim()) return
    await wrap(async () => {
      try {
        const topic = await api.subjects.createTopic({
          unit_id: unitId,
          name: form.name.trim(),
          estimated_hours: Number(form.estimated_hours),
          difficulty: Number(form.difficulty),
        })
        onAdded(topic)
        setForm({ name: '', estimated_hours: 2, difficulty: 3 })
      } catch (err) {
        toast.error('Could not add topic', err instanceof ApiError ? err.message : undefined)
      }
    })
  }

  return (
    <form onSubmit={submit} className="flex flex-wrap items-center gap-2 rounded-xl bg-muted/50 p-2.5">
      <Input
        value={form.name}
        onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
        placeholder="Topic name"
        className="min-w-[140px] flex-1"
        autoFocus
      />
      <Input
        type="number"
        min={0.25}
        step={0.25}
        value={form.estimated_hours}
        onChange={(e) => setForm((f) => ({ ...f, estimated_hours: e.target.value }))}
        className="w-20"
        title="Estimated hours"
      />
      <Select
        value={String(form.difficulty)}
        onValueChange={(v) => setForm((f) => ({ ...f, difficulty: v }))}
      >
        <SelectTrigger className="w-36">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {[1, 2, 3, 4, 5].map((d) => (
            <SelectItem key={d} value={String(d)}>
              {DIFFICULTY_LABELS[d]}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Button type="submit" size="sm" loading={pending} disabled={!form.name.trim()}>
        Add
      </Button>
      <Button type="button" size="sm" variant="ghost" onClick={onCancel}>
        Cancel
      </Button>
    </form>
  )
}

/**
 * The unit/topic tree for a subject with a generated syllabus: add/rename
 * (via edit dialog elsewhere)/reorder-free add, complete/reopen, and delete,
 * at both the unit and topic level. Shared by the standalone Syllabus page
 * and the per-subject Details page so the logic only lives in one place.
 */
function withRecomputedCompletion(unit) {
  if (!unit.topics.length) return { ...unit, completion_percentage: 0 }
  const done = unit.topics.filter((t) => t.status === 'completed').length
  return { ...unit, completion_percentage: Math.round((done / unit.topics.length) * 1000) / 10 }
}

/** The board's content statements for a topic, parsed out of the syllabus PDF. */
function KeyPoints({ topic }) {
  const [open, setOpen] = useState(false)
  const points = (topic.notes || '')
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)

  if (!points.length) return null
  const Chevron = open ? ChevronDown : ChevronRight

  return (
    <div className="mt-1.5">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground"
        aria-expanded={open}
      >
        <Chevron className="size-3.5" />
        {points.length} key {points.length === 1 ? 'point' : 'points'}
      </button>
      {open && (
        <ul className="mt-1.5 space-y-1 border-l-2 border-border/70 pl-3">
          {points.map((point, index) => (
            <li key={index} className="text-xs leading-relaxed text-muted-foreground">
              {point}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export function SyllabusTree({ subject, setSubject }) {
  const { toast } = useToast()
  const [pending, wrap] = usePending()
  const [addingTopicFor, setAddingTopicFor] = useState(null)
  const [deleteTarget, setDeleteTarget] = useState(null)

  const toggleTopic = async (topic, unitId) => {
    const done = topic.status === 'completed'
    try {
      const updated = done
        ? await api.subjects.reopenTopic(topic.id)
        : await api.subjects.completeTopic(topic.id, { confidence: 3, minutes_spent: 0 })
      setSubject((current) => ({
        ...current,
        units: current.units.map((u) =>
          u.id === unitId
            ? withRecomputedCompletion({
                ...u,
                topics: u.topics.map((t) => (t.id === topic.id ? updated : t)),
              })
            : u,
        ),
      }))
      if (!done) toast.success(`Marked "${topic.name}" complete`)
    } catch (err) {
      toast.error('Could not update topic', err instanceof ApiError ? err.message : undefined)
    }
  }

  const deleteUnit = () =>
    wrap(async () => {
      try {
        await api.subjects.removeUnit(deleteTarget.id)
        setSubject((current) => ({
          ...current,
          units: current.units.filter((u) => u.id !== deleteTarget.id),
        }))
        setDeleteTarget(null)
      } catch (err) {
        toast.error('Could not delete unit', err instanceof ApiError ? err.message : undefined)
      }
    })

  const deleteTopic = async (topic, unitId) => {
    try {
      await api.subjects.removeTopic(topic.id)
      setSubject((current) => ({
        ...current,
        units: current.units.map((u) =>
          u.id === unitId ? { ...u, topics: u.topics.filter((t) => t.id !== topic.id) } : u,
        ),
      }))
    } catch (err) {
      toast.error('Could not delete topic', err instanceof ApiError ? err.message : undefined)
    }
  }

  return (
    <div className="space-y-5">
      {subject.units.map((unit) => (
        <Card key={unit.id}>
          <CardHeader className="flex-row items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              <CardTitle>{unit.name}</CardTitle>
              <div className="mt-2 flex items-center gap-2">
                <Progress value={unit.completion_percentage} className="h-1.5 max-w-xs" />
                <span className="shrink-0 text-xs text-muted-foreground">
                  {Math.round(unit.completion_percentage)}%
                </span>
              </div>
            </div>
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={() => setDeleteTarget(unit)}
              aria-label={`Delete ${unit.name}`}
            >
              <Trash2 />
            </Button>
          </CardHeader>
          <CardContent className="space-y-2">
            {unit.topics.map((topic) => {
              const done = topic.status === 'completed'
              return (
                <div
                  key={topic.id}
                  className={cn(
                    'group flex items-start gap-3 rounded-xl border border-border/60 bg-card px-3 py-2.5',
                    done && 'bg-muted/40',
                  )}
                >
                  <div className="pt-0.5">
                    <Checkbox checked={done} onCheckedChange={() => toggleTopic(topic, unit.id)} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className={cn('text-sm font-medium', done && 'text-muted-foreground line-through')}>
                      {topic.name}
                    </p>
                    <KeyPoints topic={topic} />
                  </div>
                  <Badge variant="outline" className="mt-0.5 shrink-0">
                    {DIFFICULTY_LABELS[topic.difficulty]}
                  </Badge>
                  <span className="mt-1 shrink-0 text-xs text-muted-foreground">
                    {topic.estimated_hours}h
                  </span>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    className="opacity-0 transition-opacity group-hover:opacity-100"
                    onClick={() => deleteTopic(topic, unit.id)}
                    aria-label={`Delete ${topic.name}`}
                  >
                    <Trash2 />
                  </Button>
                </div>
              )
            })}

            {addingTopicFor === unit.id ? (
              <AddTopicForm
                unitId={unit.id}
                onCancel={() => setAddingTopicFor(null)}
                onAdded={(topic) => {
                  setSubject((current) => ({
                    ...current,
                    units: current.units.map((u) =>
                      u.id === unit.id ? { ...u, topics: [...u.topics, topic] } : u,
                    ),
                  }))
                  setAddingTopicFor(null)
                }}
              />
            ) : (
              <Button
                variant="ghost"
                size="sm"
                className="mt-1 text-muted-foreground"
                onClick={() => setAddingTopicFor(unit.id)}
              >
                <Plus /> Add topic
              </Button>
            )}
          </CardContent>
        </Card>
      ))}

      <Card>
        <CardContent className="pt-6">
          <AddUnitForm
            subjectId={subject.id}
            onAdded={(unit) => setSubject((current) => ({ ...current, units: [...current.units, unit] }))}
          />
        </CardContent>
      </Card>

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title={`Delete "${deleteTarget?.name}"?`}
        description="This deletes the unit and every topic inside it. This cannot be undone."
        confirmLabel="Delete unit"
        loading={pending}
        onConfirm={deleteUnit}
      />
    </div>
  )
}

export default SyllabusTree
