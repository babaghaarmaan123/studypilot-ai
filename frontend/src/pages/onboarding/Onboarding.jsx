import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import {
  ArrowLeft,
  ArrowRight,
  Award,
  BookOpen,
  Calendar as CalendarIcon,
  CheckCircle2,
  Loader2,
  Plus,
  Sparkles,
  Target,
  Trash2,
  Wand2,
} from 'lucide-react'

import { useAuth } from '@/context/AuthContext'
import { useToast } from '@/context/ToastContext'
import api, { ApiError } from '@/lib/api'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Progress } from '@/components/ui/progress'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'

// ---------------------------------------------------------------------------
// Small building blocks
// ---------------------------------------------------------------------------

function ChoiceCard({ selected, onClick, title, subtitle, className }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'flex flex-col items-start gap-0.5 rounded-2xl border-2 px-4 py-3 text-left text-sm transition-all',
        selected
          ? 'border-primary bg-primary/8 shadow-glow'
          : 'border-border bg-card hover:border-primary/40 hover:bg-muted',
        className,
      )}
    >
      <span className="font-semibold">{title}</span>
      {subtitle && <span className="text-xs text-muted-foreground">{subtitle}</span>}
    </button>
  )
}

function OptionGrid({ options, value, onChange, multi = false, columns = 'sm:grid-cols-2' }) {
  const values = multi ? value || [] : value

  const toggle = (optionValue) => {
    if (!multi) {
      onChange(optionValue)
      return
    }
    onChange(
      values.includes(optionValue)
        ? values.filter((v) => v !== optionValue)
        : [...values, optionValue],
    )
  }

  return (
    <div className={cn('grid grid-cols-1 gap-2.5', columns)}>
      {options.map((option) => {
        const optValue = typeof option === 'string' ? option : option.code
        const title = typeof option === 'string' ? option : option.label || option.name
        const subtitle =
          typeof option === 'string' ? undefined : option.description || option.focus || option.window
        const selected = multi ? values.includes(optValue) : values === optValue
        return (
          <ChoiceCard
            key={optValue}
            selected={selected}
            onClick={() => toggle(optValue)}
            title={title}
            subtitle={subtitle}
          />
        )
      })}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Onboarding
// ---------------------------------------------------------------------------

const EMPTY_EXAM_ROW = { subject: '', exam_board: '', exam_date: '', exam_time: '09:00', paper: '' }

export default function Onboarding() {
  const { user, refresh } = useAuth()
  const { toast } = useToast()
  const navigate = useNavigate()

  const [loading, setLoading] = useState(true)
  const [meta, setMeta] = useState(null) // { intro, catalog, questions }
  const [stage, setStage] = useState('intro') // intro | number (step index) | submitting | done
  const [answers, setAnswers] = useState({
    name: user?.name || '',
    year_group: '',
    curriculum: '',
    subjects: [],
    preparing_admission_exams: false,
    admission_exams: [],
    universities: [],
    target_degree: '',
    exams: [],
    weekday_hours: 2,
    weekend_hours: 4,
    preferred_study_time: 'evening',
    study_habits: [],
  })
  const [summary, setSummary] = useState(null)
  const savingRef = useRef(false)

  //: True when an already-onboarded student is coming back through the wizard
  //: (from the profile page), rather than filling it in for the first time.
  const isReview = Boolean(user?.onboarding_completed)

  useEffect(() => {
    let alive = true
    ;(async () => {
      try {
        const [questions, draft] = await Promise.all([
          api.onboarding.questions(),
          api.onboarding.draft(),
        ])
        if (!alive) return
        setMeta(questions)

        // A returning student's answers live on their account, not in a draft
        // (completing the wizard clears the draft), so rebuild them from the
        // profile, subjects and exam timetable. Submitting replaces all three,
        // which is only safe because what they see is what they already have.
        if (user?.onboarding_completed) {
          const [subjects, exams] = await Promise.all([
            api.subjects.list().catch(() => []),
            api.exams.list({ kind: 'school' }).catch(() => []),
          ])
          if (!alive) return
          setAnswers((current) => ({
            ...current,
            name: user.name || current.name,
            year_group: user.year_group || '',
            curriculum: user.curriculum || '',
            subjects: (subjects || []).map((s) => s.name),
            preparing_admission_exams: (user.admission_exams || []).length > 0,
            admission_exams: (user.admission_exams || []).map((e) => e.code),
            universities: user.universities || [],
            target_degree: user.target_degree || '',
            exams: (exams || []).map((e) => ({
              subject: e.subject_name || e.title,
              exam_board: e.exam_board || '',
              exam_date: e.exam_date || '',
              exam_time: e.exam_time || '09:00',
              paper: e.paper || '',
            })),
            weekday_hours: user.weekday_hours,
            weekend_hours: user.weekend_hours,
            preferred_study_time: user.preferred_study_time,
            study_habits: user.study_habits || [],
          }))
        } else if (draft?.answers && Object.keys(draft.answers).length) {
          setAnswers((current) => ({ ...current, ...draft.answers }))
          setStage(draft.step > 0 ? draft.step : 'intro')
        }
      } catch {
        toast.error('Could not load the onboarding assistant', 'Please refresh the page.')
      } finally {
        if (alive) setLoading(false)
      }
    })()
    return () => {
      alive = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const questions = meta?.questions || []
  const catalog = meta?.catalog || {}
  const currentIndex = typeof stage === 'number' ? stage : 0
  const question = questions[currentIndex]

  const set = (key, value) => setAnswers((current) => ({ ...current, [key]: value }))

  const saveDraft = async (step) => {
    if (savingRef.current) return
    savingRef.current = true
    try {
      await api.onboarding.saveDraft(step, answers)
    } catch {
      /* autosave failures are silent — the wizard still works this session */
    } finally {
      savingRef.current = false
    }
  }

  const isStepValid = useMemo(() => {
    if (!question) return true
    switch (question.key) {
      case 'name':
        return answers.name.trim().length > 0
      case 'year_group':
        return Boolean(answers.year_group)
      case 'curriculum':
        return Boolean(answers.curriculum)
      case 'subjects':
        return (answers.subjects || []).length > 0
      default:
        return true
    }
  }, [question, answers])

  const goNext = async () => {
    if (!isStepValid) return
    const nextStep = currentIndex + 1
    await saveDraft(nextStep)
    if (nextStep >= questions.length) {
      await submit()
    } else {
      setStage(nextStep)
    }
  }

  const goBack = () => {
    if (currentIndex === 0) {
      setStage('intro')
    } else {
      setStage(currentIndex - 1)
    }
  }

  const submit = async () => {
    setStage('submitting')
    try {
      const payload = {
        name: answers.name.trim(),
        year_group: answers.year_group,
        curriculum: answers.curriculum,
        subjects: answers.subjects,
        preparing_admission_exams: answers.preparing_admission_exams,
        admission_exams: answers.preparing_admission_exams ? answers.admission_exams : [],
        universities: answers.universities,
        target_degree: answers.target_degree || null,
        exams: (answers.exams || []).filter((e) => e.subject && e.exam_date),
        weekday_hours: Number(answers.weekday_hours) || 0,
        weekend_hours: Number(answers.weekend_hours) || 0,
        preferred_study_time: answers.preferred_study_time,
        study_habits: answers.study_habits,
      }
      const result = await api.onboarding.complete(payload)
      setSummary(result)
      setStage('done')
    } catch (err) {
      toast.error(
        'Could not build your study plan',
        err instanceof ApiError ? err.message : 'Please try again.',
      )
      setStage(questions.length - 1)
    }
  }

  if (loading) {
    return (
      <div className="grid min-h-screen place-items-center bg-background px-4">
        <div className="w-full max-w-lg space-y-4">
          <Skeleton className="h-8 w-2/3" />
          <Skeleton className="h-40 w-full rounded-2xl" />
          <Skeleton className="h-10 w-full rounded-xl" />
        </div>
      </div>
    )
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-background px-4 py-10 sm:py-14">
      <div className="pastel-mesh pointer-events-none absolute inset-0 -z-10" aria-hidden="true" />

      <div className="mx-auto w-full max-w-2xl">
        <AnimatePresence mode="popLayout" initial={false}>
          {stage === 'intro' && (
            <motion.div
              key="intro"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -16 }}
              transition={{ duration: 0.4 }}
              className="rounded-3xl border border-border/70 bg-card/95 p-8 text-center shadow-lift backdrop-blur sm:p-12"
            >
              <span className="mx-auto grid size-16 place-items-center rounded-3xl bg-primary text-primary-foreground">
                <Sparkles className="size-8" />
              </span>
              <h1 className="mt-6 font-display text-2xl font-bold tracking-tight sm:text-3xl">
                {isReview
                  ? "Let's update your study plan."
                  : meta?.intro?.title || "Hi! I'm your AI Study Mentor."}
              </h1>
              <p className="mx-auto mt-3 max-w-md text-sm text-muted-foreground sm:text-base">
                {isReview
                  ? 'Your profile changed, so I need to run back through these questions. ' +
                    'Everything is filled in with your current answers. Change what you ' +
                    'like and I will rebuild your subjects, timetable and plan around them.'
                  : meta?.intro?.subtitle ||
                    "I'm going to ask a few questions to create your personalised study plan."}
              </p>
              <p className="mt-1 text-xs font-medium text-muted-foreground">
                {questions.length} {isReview ? 'questions to review' : 'quick questions'} · about{' '}
                {meta?.intro?.estimated_minutes || 3} minutes
              </p>
              <Button size="lg" className="mt-8" onClick={() => setStage(0)}>
                {isReview ? 'Review my answers' : "Let's begin"} <ArrowRight />
              </Button>
            </motion.div>
          )}

          {typeof stage === 'number' && question && (
            <motion.div
              key={`question-${stage}`}
              initial={{ opacity: 0, x: 24 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -24 }}
              transition={{ duration: 0.32, ease: [0.16, 1, 0.3, 1] }}
              className="rounded-3xl border border-border/70 bg-card/95 p-6 shadow-lift backdrop-blur sm:p-9"
            >
              <div className="mb-5 flex items-center justify-between gap-4">
                <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Question {currentIndex + 1} of {questions.length}
                </span>
                <span className="text-xs font-semibold text-primary">
                  {Math.round(((currentIndex + 1) / questions.length) * 100)}%
                </span>
              </div>
              <Progress value={((currentIndex + 1) / questions.length) * 100} className="mb-7" />

              <h2 className="font-display text-xl font-bold tracking-tight sm:text-2xl">
                {question.title}
              </h2>
              {question.help && (
                <p className="mt-1.5 text-sm text-muted-foreground">{question.help}</p>
              )}

              <div className="mt-6">
                <QuestionBody
                  question={question}
                  answers={answers}
                  set={set}
                  catalog={catalog}
                />
              </div>

              <div className="mt-8 flex items-center justify-between gap-3">
                <Button variant="ghost" onClick={goBack}>
                  <ArrowLeft /> Back
                </Button>
                <Button onClick={goNext} disabled={!isStepValid}>
                  {currentIndex === questions.length - 1 ? 'Create my plan' : 'Next'}
                  <ArrowRight />
                </Button>
              </div>
            </motion.div>
          )}

          {stage === 'submitting' && (
            <motion.div
              key="submitting"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex flex-col items-center gap-4 rounded-3xl border border-border/70 bg-card/95 p-14 text-center shadow-lift backdrop-blur"
            >
              <Loader2 className="size-10 animate-spin text-primary" />
              <p className="font-display text-lg font-semibold">Building your personalised plan…</p>
              <p className="max-w-sm text-sm text-muted-foreground">
                Seeding your syllabus, scoring subject priority and scheduling your first
                28 days of study.
              </p>
            </motion.div>
          )}

          {stage === 'done' && summary && (
            <motion.div
              key="done"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              className="rounded-3xl border border-border/70 bg-card/95 p-7 shadow-lift backdrop-blur sm:p-9"
            >
              <span className="grid size-14 place-items-center rounded-2xl bg-emerald-500/15 text-emerald-600 dark:text-emerald-300">
                <CheckCircle2 className="size-7" />
              </span>
              <h2 className="mt-4 font-display text-xl font-bold tracking-tight sm:text-2xl">
                {summary.headline}
              </h2>
              <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
                {summary.summary}
              </p>

              {summary.subjects_removed > 0 && (
                <p className="mt-4 rounded-2xl border border-amber-500/40 bg-amber-500/10 p-3 text-left text-sm text-amber-700 dark:text-amber-300">
                  {summary.subjects_removed} subject
                  {summary.subjects_removed === 1 ? '' : 's'} you no longer study
                  {summary.subjects_removed === 1 ? ' was' : ' were'} removed, along
                  with its syllabus, sessions and logged past papers.
                </p>
              )}

              {summary.focus_points?.length > 0 && (
                <ul className="mt-5 space-y-2">
                  {summary.focus_points.map((point) => (
                    <li key={point} className="flex items-start gap-2 text-sm">
                      <Target className="mt-0.5 size-4 shrink-0 text-primary" />
                      {point}
                    </li>
                  ))}
                </ul>
              )}

              <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
                {[
                  [BookOpen, summary.subjects_created, 'Subjects'],
                  [Wand2, summary.topics_created, 'Topics'],
                  [CalendarIcon, summary.sessions_created, 'Sessions'],
                  [Award, summary.revisions_created, 'Revisions'],
                ].map(([Icon, value, label]) => (
                  <div key={label} className="rounded-2xl border border-border/70 bg-muted/40 p-3 text-center">
                    <Icon className="mx-auto size-4.5 text-primary" />
                    <p className="mt-1 font-display text-lg font-bold">{value}</p>
                    <p className="text-[11px] text-muted-foreground">{label}</p>
                  </div>
                ))}
              </div>

              <Button
                size="lg"
                className="mt-7 w-full"
                onClick={async () => {
                  // Only flip onboarding_completed in the auth context now —
                  // doing it earlier would make the /onboarding route guard
                  // redirect away before the student ever sees this summary.
                  await refresh()
                  navigate('/dashboard', { replace: true })
                }}
              >
                Go to my dashboard <ArrowRight />
              </Button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Per-question renderers
// ---------------------------------------------------------------------------

function QuestionBody({ question, answers, set, catalog }) {
  switch (question.key) {
    case 'name':
      return (
        <Input
          autoFocus
          value={answers.name}
          onChange={(e) => set('name', e.target.value)}
          placeholder="e.g. Alex Johnson"
          className="h-12 text-base"
        />
      )

    case 'year_group':
      return (
        <OptionGrid
          options={question.options}
          value={answers.year_group}
          onChange={(v) => set('year_group', v)}
          columns="sm:grid-cols-3"
        />
      )

    case 'curriculum':
      return (
        <OptionGrid
          options={question.options}
          value={answers.curriculum}
          onChange={(v) => {
            set('curriculum', v)
            set('subjects', [])
          }}
          columns="sm:grid-cols-1"
        />
      )

    case 'subjects': {
      const subjectOptions = catalog.subjects?.[answers.curriculum] || []
      if (!answers.curriculum) {
        return (
          <p className="rounded-xl bg-muted/60 px-4 py-6 text-center text-sm text-muted-foreground">
            Choose your curriculum on the previous question first.
          </p>
        )
      }
      return (
        <OptionGrid
          options={subjectOptions}
          value={answers.subjects}
          onChange={(v) => set('subjects', v)}
          multi
          columns="sm:grid-cols-3"
        />
      )
    }

    case 'admission_exams':
      return (
        <div className="space-y-5">
          <OptionGrid
            options={['No', 'Yes']}
            value={answers.preparing_admission_exams ? 'Yes' : 'No'}
            onChange={(v) => {
              const yes = v === 'Yes'
              set('preparing_admission_exams', yes)
              if (!yes) set('admission_exams', [])
            }}
            columns="sm:grid-cols-2"
          />
          {answers.preparing_admission_exams && (
            <div>
              <p className="mb-2.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Which tests? Select all that apply
              </p>
              <OptionGrid
                options={question.options}
                value={answers.admission_exams}
                onChange={(v) => set('admission_exams', v)}
                multi
              />
            </div>
          )}
        </div>
      )

    case 'universities':
      return (
        <OptionGrid
          options={question.options}
          value={answers.universities}
          onChange={(v) => set('universities', v)}
          multi
          columns="sm:grid-cols-2"
        />
      )

    case 'target_degree':
      return (
        <OptionGrid
          options={question.options}
          value={answers.target_degree}
          onChange={(v) => set('target_degree', v)}
          columns="sm:grid-cols-3"
        />
      )

    case 'exams':
      return (
        <ExamTable
          rows={answers.exams || []}
          onChange={(rows) => set('exams', rows)}
          subjects={answers.subjects || []}
          examBoards={catalog.exam_boards?.[answers.curriculum] || []}
        />
      )

    case 'study_hours':
      return (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="text-sm font-medium">Weekday hours / day</label>
              <Input
                type="number"
                min={0}
                max={16}
                step={0.5}
                value={answers.weekday_hours}
                onChange={(e) => set('weekday_hours', e.target.value)}
                className="mt-1.5"
              />
            </div>
            <div>
              <label className="text-sm font-medium">Weekend hours / day</label>
              <Input
                type="number"
                min={0}
                max={16}
                step={0.5}
                value={answers.weekend_hours}
                onChange={(e) => set('weekend_hours', e.target.value)}
                className="mt-1.5"
              />
            </div>
          </div>
          <div>
            <p className="mb-2.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Preferred study time
            </p>
            <OptionGrid
              options={question.options}
              value={answers.preferred_study_time}
              onChange={(v) => set('preferred_study_time', v)}
              columns="sm:grid-cols-2"
            />
          </div>
        </div>
      )

    case 'study_habits':
      return (
        <OptionGrid
          options={question.options}
          value={answers.study_habits}
          onChange={(v) => set('study_habits', v)}
          multi
          columns="sm:grid-cols-1"
        />
      )

    default:
      return null
  }
}

function ExamTable({ rows, onChange, subjects, examBoards }) {
  const addRow = () => onChange([...rows, { ...EMPTY_EXAM_ROW }])
  const removeRow = (index) => onChange(rows.filter((_, i) => i !== index))
  const updateRow = (index, field, value) =>
    onChange(rows.map((row, i) => (i === index ? { ...row, [field]: value } : row)))

  return (
    <div className="space-y-3">
      {rows.length === 0 && (
        <p className="rounded-xl bg-muted/60 px-4 py-5 text-center text-sm text-muted-foreground">
          No exams yet. You can skip this and add them later.
        </p>
      )}

      {rows.map((row, index) => (
        <div key={index} className="grid gap-2.5 rounded-2xl border border-border/70 bg-muted/30 p-3.5 sm:grid-cols-12">
          <div className="sm:col-span-4">
            <Select value={row.subject} onValueChange={(v) => updateRow(index, 'subject', v)}>
              <SelectTrigger>
                <SelectValue placeholder="Subject" />
              </SelectTrigger>
              <SelectContent>
                {subjects.map((s) => (
                  <SelectItem key={s} value={s}>
                    {s}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="sm:col-span-3">
            <Select
              value={row.exam_board || undefined}
              onValueChange={(v) => updateRow(index, 'exam_board', v)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Exam board" />
              </SelectTrigger>
              <SelectContent>
                {examBoards.map((board) => (
                  <SelectItem key={board} value={board}>
                    {board}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="sm:col-span-2">
            <Input
              type="date"
              value={row.exam_date}
              onChange={(e) => updateRow(index, 'exam_date', e.target.value)}
            />
          </div>
          <div className="sm:col-span-2">
            <Input
              type="time"
              value={row.exam_time}
              onChange={(e) => updateRow(index, 'exam_time', e.target.value)}
            />
          </div>
          <div className="flex items-center justify-end sm:col-span-1">
            <Button variant="ghost" size="icon-sm" onClick={() => removeRow(index)} aria-label="Remove exam">
              <Trash2 />
            </Button>
          </div>
        </div>
      ))}

      <Button variant="outline" size="sm" onClick={addRow} disabled={subjects.length === 0}>
        <Plus /> Add exam
      </Button>
    </div>
  )
}
