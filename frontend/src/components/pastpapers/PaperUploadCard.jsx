import { useRef, useState } from 'react'
import { FileUp, Loader2, UploadCloud } from 'lucide-react'

import { cn } from '@/lib/utils'

import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

const AUTO = 'auto'

/**
 * The primary way to add a past paper: drop the PDF in. Subject, board, year,
 * paper number, total marks and time allowed are read off the cover page, so
 * the only thing left to type is the score — and that happens inline on the
 * paper's row once it has been marked.
 */
export function PaperUploadCard({ subjects, uploading, onUpload }) {
  const fileRef = useRef(null)
  const [dragging, setDragging] = useState(false)
  const [subjectId, setSubjectId] = useState(AUTO)

  const send = (files) => {
    const chosen = Array.from(files || []).filter((file) =>
      file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf'),
    )
    if (chosen.length) onUpload(chosen, subjectId === AUTO ? '' : subjectId)
  }

  return (
    <Card>
      <CardContent className="pt-6">
        <div
          onDragOver={(event) => {
            event.preventDefault()
            setDragging(true)
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => {
            event.preventDefault()
            setDragging(false)
            send(event.dataTransfer.files)
          }}
          onClick={() => !uploading && fileRef.current?.click()}
          role="button"
          tabIndex={0}
          onKeyDown={(event) => {
            if (event.key === 'Enter' || event.key === ' ') fileRef.current?.click()
          }}
          className={cn(
            'flex cursor-pointer flex-col items-center gap-3 rounded-2xl border-2 border-dashed border-border px-4 py-10 text-center transition-colors',
            'hover:border-primary/60 hover:bg-primary/[0.03]',
            dragging && 'border-primary bg-primary/5',
            uploading && 'pointer-events-none opacity-70',
          )}
        >
          <input
            ref={fileRef}
            type="file"
            accept="application/pdf"
            multiple
            className="hidden"
            onChange={(event) => {
              send(event.target.files)
              event.target.value = ''
            }}
          />

          <span className="grid size-12 place-items-center rounded-2xl bg-primary/10 text-primary">
            {uploading ? (
              <Loader2 className="size-6 animate-spin" />
            ) : (
              <UploadCloud className="size-6" />
            )}
          </span>

          <div>
            <p className="text-sm font-semibold">
              {uploading ? 'Reading your paper…' : 'Drop a past paper PDF here'}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              {uploading
                ? 'Reading the subject, board, year and total marks off the cover page.'
                : 'Or click to browse. Add your score once it is marked.'}
            </p>
          </div>

          <Button variant="subtle" size="sm" type="button" loading={uploading}>
            <FileUp /> Choose PDF
          </Button>
        </div>

        <div className="mt-4 flex flex-wrap items-center justify-center gap-2 text-xs text-muted-foreground">
          <span>Subject:</span>
          <Select value={subjectId} onValueChange={setSubjectId}>
            <SelectTrigger className="h-8 w-52 text-xs" onClick={(e) => e.stopPropagation()}>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={AUTO}>Detect from the paper</SelectItem>
              {(subjects || []).map((subject) => (
                <SelectItem key={subject.id} value={String(subject.id)}>
                  {subject.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </CardContent>
    </Card>
  )
}

export default PaperUploadCard
