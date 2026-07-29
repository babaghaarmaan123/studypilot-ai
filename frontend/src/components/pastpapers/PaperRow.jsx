import { useState } from 'react'
import { Check, ExternalLink, MoreVertical, Pencil, Trash2 } from 'lucide-react'

import { assetUrl } from '@/lib/api'
import { formatDate } from '@/lib/utils'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Input } from '@/components/ui/input'

/** Inline "what did you get?" form — replaces the old add-a-paper dialog. */
function ScoreForm({ paper, pending, onSave }) {
  const [scored, setScored] = useState('')
  const [total, setTotal] = useState(String(paper.marks_total ?? ''))
  const [minutes, setMinutes] = useState(
    paper.time_taken_minutes ? String(paper.time_taken_minutes) : '',
  )

  const valid = scored !== '' && Number(total) > 0 && Number(scored) <= Number(total)

  return (
    <form
      className="mt-2.5 flex flex-wrap items-end gap-2 rounded-xl bg-muted/50 p-2.5"
      onSubmit={(event) => {
        event.preventDefault()
        if (!valid) return
        onSave({
          marks_scored: Number(scored),
          marks_total: Number(total),
          time_taken_minutes: minutes ? Number(minutes) : null,
        })
      }}
    >
      <label className="flex flex-col gap-1">
        <span className="text-[11px] font-medium text-muted-foreground">Your marks</span>
        <Input
          type="number"
          min={0}
          value={scored}
          onChange={(event) => setScored(event.target.value)}
          className="h-9 w-24"
          placeholder="58"
          autoFocus
        />
      </label>
      <span className="pb-2.5 text-sm text-muted-foreground">/</span>
      <label className="flex flex-col gap-1">
        <span className="text-[11px] font-medium text-muted-foreground">Out of</span>
        <Input
          type="number"
          min={1}
          value={total}
          onChange={(event) => setTotal(event.target.value)}
          className="h-9 w-24"
        />
      </label>
      <label className="flex flex-col gap-1">
        <span className="text-[11px] font-medium text-muted-foreground">Minutes</span>
        <Input
          type="number"
          min={0}
          value={minutes}
          onChange={(event) => setMinutes(event.target.value)}
          className="h-9 w-24"
          placeholder="90"
        />
      </label>
      <Button type="submit" size="sm" loading={pending} disabled={!valid}>
        <Check /> Save score
      </Button>
    </form>
  )
}

/** One logged paper: metadata, the PDF link, and its score (or the score form). */
export function PaperRow({ paper, pending, onScore, onEdit, onDelete }) {
  const meta = [
    paper.exam_board,
    paper.paper,
    paper.year,
    paper.session_label,
  ].filter(Boolean)

  return (
    <div className="relative overflow-hidden rounded-2xl border border-border/70 bg-card p-4">
      <span
        className="absolute inset-y-0 left-0 w-1.5"
        style={{ backgroundColor: paper.subject_colour }}
        aria-hidden="true"
      />
      <div className="ml-1.5 flex items-start gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <Badge variant="outline">{paper.subject_name}</Badge>
            {meta.map((item) => (
              <Badge key={item} variant="secondary">
                {item}
              </Badge>
            ))}
            {!paper.scored && <Badge variant="warning">Awaiting score</Badge>}
            <span className="text-xs text-muted-foreground">
              {formatDate(paper.date_taken)}
            </span>
          </div>

          <h4 className="mt-1 truncate text-sm font-semibold">{paper.title}</h4>

          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            {paper.scored && (
              <p className="text-xs text-muted-foreground">
                {paper.marks_scored}/{paper.marks_total} marks
                {paper.time_taken_minutes ? ` · ${paper.time_taken_minutes} min` : ''}
              </p>
            )}
            {paper.file_url && (
              <a
                href={assetUrl(paper.file_url)}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
              >
                <ExternalLink className="size-3" />
                Open PDF
              </a>
            )}
          </div>

          {!paper.scored && (
            <ScoreForm
              paper={paper}
              pending={pending}
              onSave={(body) => onScore(paper, body)}
            />
          )}
        </div>

        <div className="flex shrink-0 items-center gap-3">
          {paper.scored && (
            <div className="text-right">
              <p className="font-display text-lg font-bold text-primary">
                {paper.percentage}%
              </p>
              {paper.grade && <Badge variant="success">{paper.grade}</Badge>}
            </div>
          )}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon-sm" aria-label="Paper actions">
                <MoreVertical />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onSelect={() => onEdit(paper)}>
                <Pencil /> Edit details
              </DropdownMenuItem>
              <DropdownMenuItem destructive onSelect={() => onDelete(paper)}>
                <Trash2 /> Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </div>
  )
}

export default PaperRow
