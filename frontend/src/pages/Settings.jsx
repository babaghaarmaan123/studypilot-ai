import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import jsPDF from 'jspdf'
import autoTable from 'jspdf-autotable'
import {
  Download,
  KeyRound,
  Laptop,
  Moon,
  Settings as SettingsIcon,
  ShieldAlert,
  Sun,
} from 'lucide-react'

import { useAuth } from '@/context/AuthContext'
import { useTheme } from '@/context/ThemeContext'
import { useToast } from '@/context/ToastContext'
import { useFetch, usePending } from '@/hooks/useFetch'
import api, { ApiError } from '@/lib/api'
import { cn } from '@/lib/utils'

import { PageHeader } from '@/components/PageHeader'
import { ConfirmDialog } from '@/components/ConfirmDialog'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Field } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'

const THEME_OPTIONS = [
  { value: 'light', label: 'Light', icon: Sun },
  { value: 'dark', label: 'Dark', icon: Moon },
  { value: 'system', label: 'System', icon: Laptop },
]

const TOGGLES = [
  { key: 'notifications_enabled', label: 'In-app notifications', hint: 'Bell alerts for reminders and milestones.' },
  { key: 'study_reminders', label: 'Study reminders', hint: 'Nudges before your scheduled sessions.' },
  { key: 'email_reminders', label: 'Daily plan email', hint: "A morning email listing that day's sessions." },
  { key: 'weekly_report', label: 'Weekly report', hint: 'A summary of your progress every week.' },
  { key: 'calendar_sync', label: 'Calendar sync', hint: 'Keep your timetable mirrored to your calendar.' },
  { key: 'auto_reschedule', label: 'Auto-reschedule', hint: 'Automatically rebuild your plan after missed sessions.' },
]

export default function Settings() {
  const { signOut } = useAuth()
  const { theme, setTheme } = useTheme()
  const { toast } = useToast()
  const navigate = useNavigate()

  const { data: settings, setData: setSettings } = useFetch(() => api.users.settings(), [])
  const [pending, wrap] = usePending()
  const [exporting, wrapExport] = usePending()

  const [passwordForm, setPasswordForm] = useState({ current_password: '', new_password: '', confirm: '' })
  const [passwordError, setPasswordError] = useState('')
  const [passwordPending, wrapPassword] = usePending()
  const [deleteOpen, setDeleteOpen] = useState(false)

  const updateSetting = (key, value) =>
    wrap(async () => {
      try {
        const updated = await api.users.updateSettings({ [key]: value })
        setSettings(updated)
      } catch (err) {
        toast.error('Could not save that setting', err instanceof ApiError ? err.message : undefined)
      }
    })

  const changeTheme = (value) => {
    setTheme(value)
    updateSetting('theme', value)
  }

  const submitPassword = (event) => {
    event.preventDefault()
    setPasswordError('')
    if (passwordForm.new_password !== passwordForm.confirm) {
      setPasswordError('New passwords do not match.')
      return
    }
    wrapPassword(async () => {
      try {
        await api.auth.changePassword({
          current_password: passwordForm.current_password,
          new_password: passwordForm.new_password,
        })
        toast.success('Password changed')
        setPasswordForm({ current_password: '', new_password: '', confirm: '' })
      } catch (err) {
        setPasswordError(err instanceof ApiError ? err.message : 'Something went wrong.')
      }
    })
  }

  const exportPdf = () =>
    wrapExport(async () => {
      try {
        const data = await api.users.exportTimetable()
        const doc = new jsPDF()

        doc.setFontSize(18)
        doc.text('StudyPilot AI Study Timetable', 14, 18)
        doc.setFontSize(10)
        doc.setTextColor(100)
        doc.text(`Generated ${data.generated_on}`, 14, 25)
        doc.text(
          `${data.student.name} · ${data.student.curriculum || ''} ${data.student.year_group || ''}`.trim(),
          14,
          30,
        )

        autoTable(doc, {
          startY: 38,
          head: [['Subject', 'Exam board', 'Difficulty', 'Progress']],
          body: data.subjects.map((s) => [
            s.name,
            s.exam_board || '-',
            `${s.difficulty}/5`,
            `${Math.round(s.completion_percentage)}%`,
          ]),
          headStyles: { fillColor: [99, 102, 241] },
        })

        autoTable(doc, {
          startY: doc.lastAutoTable.finalY + 10,
          head: [['Exam', 'Date', 'Time', 'Board']],
          body: data.exams.map((e) => [e.title, e.exam_date, e.exam_time || '-', e.exam_board || '-']),
          headStyles: { fillColor: [99, 102, 241] },
        })

        autoTable(doc, {
          startY: doc.lastAutoTable.finalY + 10,
          head: [['Date', 'Time', 'Session', 'Duration']],
          body: data.sessions.map((s) => [
            s.session_date,
            s.start_time,
            s.title,
            `${s.duration_minutes} min`,
          ]),
          headStyles: { fillColor: [99, 102, 241] },
        })

        doc.save(`studypilot-timetable-${data.generated_on}.pdf`)
        toast.success('Timetable exported')
      } catch (err) {
        toast.error('Could not export your timetable', err instanceof ApiError ? err.message : undefined)
      }
    })

  const deleteAccount = () =>
    wrap(async () => {
      try {
        await api.users.deleteAccount()
        signOut()
        toast.info('Account deleted')
        navigate('/', { replace: true })
      } catch (err) {
        toast.error('Could not delete account', err instanceof ApiError ? err.message : undefined)
      }
    })

  return (
    <div className="space-y-6">
      <PageHeader
        title="Settings"
        description="Appearance, notifications and account controls."
        icon={SettingsIcon}
      />

      <Card>
        <CardHeader>
          <CardTitle>Appearance</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-3">
            {THEME_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                onClick={() => changeTheme(opt.value)}
                className={cn(
                  'flex flex-col items-center gap-2 rounded-2xl border-2 px-4 py-4 transition-all',
                  theme === opt.value
                    ? 'border-primary bg-primary/8'
                    : 'border-border hover:border-primary/40 hover:bg-muted',
                )}
              >
                <opt.icon className="size-5" />
                <span className="text-sm font-semibold">{opt.label}</span>
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Notifications & sync</CardTitle>
        </CardHeader>
        <CardContent className="divide-y divide-border/60">
          {TOGGLES.map((toggle) => (
            <div key={toggle.key} className="flex items-center justify-between gap-4 py-3 first:pt-0 last:pb-0">
              <div>
                <p className="text-sm font-medium">{toggle.label}</p>
                <p className="text-xs text-muted-foreground">{toggle.hint}</p>
              </div>
              <Switch
                checked={Boolean(settings?.[toggle.key])}
                disabled={!settings || pending}
                onCheckedChange={(v) => updateSetting(toggle.key, v)}
              />
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Download className="size-4.5 text-primary" /> Export timetable
          </CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-between gap-4">
          <p className="text-sm text-muted-foreground">
            Download your subjects, exams and next 28 days as a PDF.
          </p>
          <Button variant="outline" loading={exporting} onClick={exportPdf}>
            <Download /> Export PDF
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <KeyRound className="size-4.5 text-primary" /> Change password
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={submitPassword} className="grid gap-4 sm:grid-cols-3">
            <Field label="Current password">
              <Input
                type="password"
                value={passwordForm.current_password}
                onChange={(e) => setPasswordForm((f) => ({ ...f, current_password: e.target.value }))}
                required
              />
            </Field>
            <Field label="New password">
              <Input
                type="password"
                minLength={8}
                value={passwordForm.new_password}
                onChange={(e) => setPasswordForm((f) => ({ ...f, new_password: e.target.value }))}
                required
              />
            </Field>
            <Field label="Confirm new password">
              <Input
                type="password"
                minLength={8}
                value={passwordForm.confirm}
                onChange={(e) => setPasswordForm((f) => ({ ...f, confirm: e.target.value }))}
                required
              />
            </Field>
            {passwordError && (
              <p className="sm:col-span-3 text-sm font-medium text-destructive">{passwordError}</p>
            )}
            <div className="sm:col-span-3">
              <Button type="submit" loading={passwordPending}>
                Update password
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card className="border-destructive/30">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-destructive">
            <ShieldAlert className="size-4.5" /> Danger zone
          </CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-between gap-4">
          <p className="text-sm text-muted-foreground">
            Permanently delete your account and every subject, plan, session and paper. This
            cannot be undone.
          </p>
          <Button variant="destructive" onClick={() => setDeleteOpen(true)}>
            Delete account
          </Button>
        </CardContent>
      </Card>

      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Delete your account?"
        description="This permanently deletes your account and all associated data. This cannot be undone."
        confirmLabel="Delete my account"
        confirmPhrase="DELETE"
        loading={pending}
        onConfirm={deleteAccount}
      />
    </div>
  )
}
