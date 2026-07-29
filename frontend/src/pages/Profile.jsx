import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Camera, Save, Trash2, UserRound } from 'lucide-react'

import { useAuth } from '@/context/AuthContext'
import { useToast } from '@/context/ToastContext'
import { useFetch, usePending } from '@/hooks/useFetch'
import api, { ApiError } from '@/lib/api'
import { CURRICULUM_LABELS } from '@/lib/utils'

import { PageHeader } from '@/components/PageHeader'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Field } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Progress } from '@/components/ui/progress'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { UserAvatar } from '@/components/ui/avatar'

export default function Profile() {
  const { user, patchUser } = useAuth()
  const { toast } = useToast()
  const navigate = useNavigate()
  const { data: catalog } = useFetch(() => api.catalog.all(), [])
  const [pending, wrap] = usePending()
  const [avatarPending, wrapAvatar] = usePending()
  const fileRef = useRef(null)

  const [form, setForm] = useState({
    name: user?.name || '',
    year_group: user?.year_group || '',
    curriculum: user?.curriculum || '',
    target_degree: user?.target_degree || '',
    weekday_hours: user?.weekday_hours ?? 2,
    weekend_hours: user?.weekend_hours ?? 4,
    preferred_study_time: user?.preferred_study_time || 'evening',
    study_habits: user?.study_habits || [],
    universities: user?.universities || [],
  })

  useEffect(() => {
    if (!user) return
    setForm({
      name: user.name,
      year_group: user.year_group || '',
      curriculum: user.curriculum || '',
      target_degree: user.target_degree || '',
      weekday_hours: user.weekday_hours,
      weekend_hours: user.weekend_hours,
      preferred_study_time: user.preferred_study_time,
      study_habits: user.study_habits || [],
      universities: user.universities || [],
    })
  }, [user])

  const toggleList = (key, value) =>
    setForm((f) => ({
      ...f,
      [key]: f[key].includes(value) ? f[key].filter((v) => v !== value) : [...f[key], value],
    }))

  const save = () =>
    wrap(async () => {
      try {
        const updated = await api.users.updateProfile({
          name: form.name,
          year_group: form.year_group || null,
          curriculum: form.curriculum || null,
          target_degree: form.target_degree || null,
          weekday_hours: Number(form.weekday_hours),
          weekend_hours: Number(form.weekend_hours),
          preferred_study_time: form.preferred_study_time,
          study_habits: form.study_habits,
          universities: form.universities,
        })
        patchUser(updated)
        toast.success(
          'Profile saved',
          'Now confirm your answers so your plan matches them.',
        )
        // Saving the profile changes the inputs the planner runs on, but not the
        // subjects, timetable or plan themselves. Sending the student back
        // through the ten questions — pre-filled — is what actually rebuilds
        // those, so the dashboard ends up agreeing with the profile.
        navigate('/onboarding')
      } catch (err) {
        toast.error('Could not save your profile', err instanceof ApiError ? err.message : undefined)
      }
    })

  const handleAvatarPick = () => fileRef.current?.click()

  const handleAvatarChange = (event) => {
    const file = event.target.files?.[0]
    if (!file) return
    wrapAvatar(async () => {
      try {
        const updated = await api.users.uploadAvatar(file)
        patchUser(updated)
        toast.success('Profile picture updated')
      } catch (err) {
        toast.error('Could not upload image', err instanceof ApiError ? err.message : undefined)
      } finally {
        event.target.value = ''
      }
    })
  }

  const removeAvatar = () =>
    wrapAvatar(async () => {
      try {
        const updated = await api.users.removeAvatar()
        patchUser(updated)
        toast.info('Profile picture removed')
      } catch (err) {
        toast.error('Could not remove image', err instanceof ApiError ? err.message : undefined)
      }
    })

  const setAdmissionDate = async (examId, date) => {
    try {
      await api.exams.setAdmissionDate(examId, date)
      toast.success('Admissions exam date saved')
    } catch (err) {
      toast.error('Could not save date', err instanceof ApiError ? err.message : undefined)
    }
  }

  if (!user) return null

  return (
    <div className="space-y-6">
      <PageHeader
        title="Profile"
        description="Keep your study profile up to date so the AI planner stays accurate."
        icon={UserRound}
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-1">
          <CardContent className="flex flex-col items-center pt-6 text-center">
            <UserAvatar user={user} className="size-24" />
            <input
              ref={fileRef}
              type="file"
              accept="image/png,image/jpeg,image/webp,image/gif"
              className="hidden"
              onChange={handleAvatarChange}
            />
            <div className="mt-4 flex gap-2">
              <Button size="sm" variant="outline" loading={avatarPending} onClick={handleAvatarPick}>
                <Camera /> Change
              </Button>
              {user.avatar_url && (
                <Button size="sm" variant="ghost" onClick={removeAvatar} disabled={avatarPending}>
                  <Trash2 /> Remove
                </Button>
              )}
            </div>

            <h2 className="mt-4 font-display text-lg font-bold">{user.name}</h2>
            <p className="text-sm text-muted-foreground">{user.email}</p>

            <div className="mt-4 flex flex-wrap justify-center gap-1.5">
              {user.curriculum && (
                <Badge variant="outline">{CURRICULUM_LABELS[user.curriculum]}</Badge>
              )}
              {user.year_group && <Badge variant="secondary">{user.year_group}</Badge>}
            </div>

            <div className="mt-5 w-full border-t border-border/60 pt-4 text-left text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">XP</span>
                <span className="font-semibold">{user.xp}</span>
              </div>
              <div className="mt-1.5 flex justify-between">
                <span className="text-muted-foreground">Streak</span>
                <span className="font-semibold">{user.streak_current} days</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Study profile</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Field label="Full name">
              <Input value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} />
            </Field>

            <div className="grid grid-cols-2 gap-3">
              <Field label="Year group">
                <Select
                  value={form.year_group || undefined}
                  onValueChange={(v) => setForm((f) => ({ ...f, year_group: v }))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select" />
                  </SelectTrigger>
                  <SelectContent>
                    {(catalog?.year_groups || []).map((yg) => (
                      <SelectItem key={yg} value={yg}>
                        {yg}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>
              <Field label="Curriculum">
                <Select
                  value={form.curriculum || undefined}
                  onValueChange={(v) => setForm((f) => ({ ...f, curriculum: v }))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select" />
                  </SelectTrigger>
                  <SelectContent>
                    {(catalog?.curricula || []).map((c) => (
                      <SelectItem key={c.code} value={c.code}>
                        {c.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>
            </div>

            <Field label="Target degree">
              <Select
                value={form.target_degree || undefined}
                onValueChange={(v) => setForm((f) => ({ ...f, target_degree: v }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select" />
                </SelectTrigger>
                <SelectContent>
                  {(catalog?.degrees || []).map((d) => (
                    <SelectItem key={d} value={d}>
                      {d}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>

            <div className="grid grid-cols-3 gap-3">
              <Field label="Weekday hours">
                <Input
                  type="number"
                  min={0}
                  max={16}
                  step={0.5}
                  value={form.weekday_hours}
                  onChange={(e) => setForm((f) => ({ ...f, weekday_hours: e.target.value }))}
                />
              </Field>
              <Field label="Weekend hours">
                <Input
                  type="number"
                  min={0}
                  max={16}
                  step={0.5}
                  value={form.weekend_hours}
                  onChange={(e) => setForm((f) => ({ ...f, weekend_hours: e.target.value }))}
                />
              </Field>
              <Field label="Preferred time">
                <Select
                  value={form.preferred_study_time}
                  onValueChange={(v) => setForm((f) => ({ ...f, preferred_study_time: v }))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {(catalog?.preferred_study_times || []).map((t) => (
                      <SelectItem key={t.code} value={t.code}>
                        {t.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>
            </div>

            <Field label="Study habits">
              <div className="flex flex-wrap gap-2">
                {(catalog?.study_habits || []).map((habit) => (
                  <button
                    key={habit.code}
                    type="button"
                    onClick={() => toggleList('study_habits', habit.code)}
                    className={`rounded-full border px-3 py-1.5 text-xs font-medium transition-colors ${
                      form.study_habits.includes(habit.code)
                        ? 'border-primary bg-primary/10 text-primary'
                        : 'border-border text-muted-foreground hover:bg-muted'
                    }`}
                  >
                    {habit.label}
                  </button>
                ))}
              </div>
            </Field>

            <Field label="Target universities">
              <div className="flex max-h-40 flex-wrap gap-2 overflow-y-auto">
                {(catalog?.universities || []).map((uni) => (
                  <button
                    key={uni}
                    type="button"
                    onClick={() => toggleList('universities', uni)}
                    className={`rounded-full border px-3 py-1.5 text-xs font-medium transition-colors ${
                      form.universities.includes(uni)
                        ? 'border-primary bg-primary/10 text-primary'
                        : 'border-border text-muted-foreground hover:bg-muted'
                    }`}
                  >
                    {uni}
                  </button>
                ))}
              </div>
            </Field>

            <div className="flex flex-wrap items-center gap-3">
              <Button onClick={save} loading={pending}>
                <Save /> Save changes
              </Button>
              <p className="text-xs text-muted-foreground">
                Saving takes you back through the ten questions so your subjects,
                timetable and plan are rebuilt to match.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {user.admission_exams.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Admissions tests</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {user.admission_exams.map((exam) => (
              <div
                key={exam.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border/60 p-3"
              >
                <div>
                  <p className="text-sm font-semibold">{exam.name}</p>
                  <div className="mt-1 flex items-center gap-2">
                    <Progress value={exam.preparation_percentage} className="h-1.5 w-32" />
                    <span className="text-xs text-muted-foreground">
                      {Math.round(exam.preparation_percentage)}% ready
                    </span>
                  </div>
                </div>
                <Input
                  type="date"
                  defaultValue={exam.exam_date || ''}
                  onChange={(e) => setAdmissionDate(exam.id, e.target.value)}
                  className="w-auto"
                />
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
