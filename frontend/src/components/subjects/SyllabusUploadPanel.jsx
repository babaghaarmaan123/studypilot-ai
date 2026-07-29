import { useRef, useState } from 'react'
import { FileUp, Loader2, UploadCloud } from 'lucide-react'

import { useToast } from '@/context/ToastContext'
import api, { ApiError } from '@/lib/api'
import { SYLLABUS_STATUS_META, cn } from '@/lib/utils'

import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'

const EXAMPLES = [
  'Pearson Edexcel IAL Computer Science Specification',
  'AQA GCSE Mathematics',
  'OCR A Level Physics',
  'Cambridge International Chemistry',
]

/** The "upload your syllabus PDF" prompt shown until a subject has one. */
export function SyllabusUploadPanel({ subject, onUploaded }) {
  const { toast } = useToast()
  const fileRef = useRef(null)
  const [uploading, setUploading] = useState(false)
  const statusMeta = SYLLABUS_STATUS_META[subject.syllabus_status] || SYLLABUS_STATUS_META.not_uploaded
  const isReplace = subject.syllabus_status !== 'not_uploaded'

  const handleFile = async (event) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    setUploading(true)
    try {
      const updated = await api.subjects.uploadSyllabusPdf(subject.id, file)
      onUploaded(updated)
      toast.success(`Syllabus generated for ${subject.name}`)
    } catch (err) {
      toast.error('Could not process that PDF', err instanceof ApiError ? err.message : undefined)
    } finally {
      setUploading(false)
    }
  }

  return (
    <Card>
      <CardContent className="flex flex-col items-center gap-4 py-12 text-center">
        <input ref={fileRef} type="file" accept="application/pdf" className="hidden" onChange={handleFile} />

        <span className="grid size-14 place-items-center rounded-2xl bg-primary/10 text-primary">
          {uploading ? <Loader2 className="size-7 animate-spin" /> : <UploadCloud className="size-7" />}
        </span>

        <div>
          <p className="flex items-center justify-center gap-1.5 text-sm font-medium">
            <span className={cn('size-2.5 rounded-full', statusMeta.dot)} />
            {statusMeta.label}
          </p>
          <p className="mx-auto mt-2 max-w-sm text-sm text-muted-foreground">
            {uploading
              ? 'Extracting units, topics and estimated hours from your specification…'
              : 'Upload your official syllabus PDF to begin creating your study plan.'}
          </p>
        </div>

        <Button onClick={() => fileRef.current?.click()} loading={uploading}>
          <FileUp /> {isReplace ? 'Replace syllabus PDF' : 'Upload PDF'}
        </Button>

        {!isReplace && (
          <div className="mt-2 text-xs text-muted-foreground">
            <p className="font-medium">Examples of what to upload:</p>
            <ul className="mt-1 space-y-0.5">
              {EXAMPLES.map((example) => (
                <li key={example}>{example}</li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default SyllabusUploadPanel
