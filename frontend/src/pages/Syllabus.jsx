import { useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { BookOpen, ListTree } from 'lucide-react'

import { useFetch } from '@/hooks/useFetch'
import api from '@/lib/api'

import { PageHeader } from '@/components/PageHeader'
import { SyllabusTree } from '@/components/subjects/SyllabusTree'
import { SyllabusUploadPanel } from '@/components/subjects/SyllabusUploadPanel'
import { Button } from '@/components/ui/button'
import { EmptyState } from '@/components/ui/empty-state'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { SkeletonCard } from '@/components/ui/skeleton'

export default function Syllabus() {
  const { subjectId } = useParams()
  const navigate = useNavigate()
  const { data: subjects } = useFetch(() => api.subjects.list(), [])

  const activeId = subjectId ? Number(subjectId) : subjects?.[0]?.id

  const {
    data: subject,
    loading,
    error,
    setData: setSubject,
  } = useFetch(() => (activeId ? api.subjects.get(activeId) : Promise.resolve(null)), [activeId], {
    enabled: Boolean(activeId),
  })

  useEffect(() => {
    if (!subjectId && subjects?.length) {
      navigate(`/syllabus/${subjects[0].id}`, { replace: true })
    }
  }, [subjectId, subjects, navigate])

  return (
    <div className="space-y-6">
      <PageHeader
        title="Syllabus"
        description="Break each subject into units and topics, then mark them off as you go."
        icon={ListTree}
        actions={
          subjects?.length ? (
            <Select
              value={activeId ? String(activeId) : undefined}
              onValueChange={(v) => navigate(`/syllabus/${v}`)}
            >
              <SelectTrigger className="w-56">
                <SelectValue placeholder="Choose a subject" />
              </SelectTrigger>
              <SelectContent>
                {subjects.map((s) => (
                  <SelectItem key={s.id} value={String(s.id)}>
                    {s.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : null
        }
      />

      {!subjects || loading ? (
        <div className="space-y-3">
          <SkeletonCard />
          <SkeletonCard />
        </div>
      ) : subjects.length === 0 ? (
        <EmptyState
          icon={BookOpen}
          title="Add a subject first"
          description="Create a subject from the Subjects page, then come back here to build its syllabus."
          action={
            <Button onClick={() => navigate('/subjects')}>
              <BookOpen /> Go to Subjects
            </Button>
          }
        />
      ) : error || !subject ? (
        <EmptyState icon={ListTree} title="Couldn't load this syllabus" description={error?.message} />
      ) : subject.syllabus_status !== 'ready' || subject.units.length === 0 ? (
        <SyllabusUploadPanel subject={subject} onUploaded={setSubject} />
      ) : (
        <SyllabusTree subject={subject} setSubject={setSubject} />
      )}
    </div>
  )
}
