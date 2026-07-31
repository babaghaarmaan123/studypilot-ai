import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { KeyRound, MailCheck } from 'lucide-react'

import { AuthLayout } from '@/components/layout/AuthLayout'
import { Button } from '@/components/ui/button'
import { Field } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import api, { ApiError } from '@/lib/api'

const CODE_LENGTH = 6

export default function ResetPassword() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()

  const [email, setEmail] = useState(searchParams.get('email') || '')
  // Prefilled only when the backend is in debug with no mail server, so the
  // flow can be walked through locally.
  const [code, setCode] = useState(searchParams.get('code') || '')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [resending, setResending] = useState(false)
  const [resent, setResent] = useState(false)
  const [done, setDone] = useState(false)

  const arrivedFromRequest = Boolean(searchParams.get('email'))

  const handleSubmit = async (event) => {
    event.preventDefault()
    setError('')

    if (password !== confirm) {
      setError('Passwords do not match.')
      return
    }

    setLoading(true)
    try {
      await api.auth.resetPassword({ email: email.trim(), code: code.trim(), password })
      setDone(true)
      setTimeout(() => navigate('/login', { replace: true }), 1500)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const resend = async () => {
    if (!email.trim()) {
      setError('Enter your email address first.')
      return
    }
    setError('')
    setResending(true)
    try {
      const response = await api.auth.forgotPassword(email.trim())
      setResent(true)
      if (response?.reset_code) setCode(response.reset_code)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not send a new code.')
    } finally {
      setResending(false)
    }
  }

  if (done) {
    return (
      <AuthLayout title="Password updated" subtitle="Redirecting you to sign in...">
        <div className="flex flex-col items-center gap-3 py-6 text-center">
          <span className="grid size-14 place-items-center rounded-2xl bg-success/15 text-success">
            <KeyRound className="size-7" />
          </span>
          <p className="text-sm text-muted-foreground">
            Your password has been changed. You can sign in now.
          </p>
        </div>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout
      title="Enter your reset code"
      subtitle="Check your email for a six digit code, then choose a new password."
      footer={
        <Link to="/login" className="font-semibold text-primary hover:underline">
          Back to login
        </Link>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        {arrivedFromRequest && !resent && (
          <p className="flex items-start gap-2 rounded-xl bg-primary/8 px-3.5 py-2.5 text-sm text-foreground">
            <MailCheck className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden="true" />
            <span>
              If an account exists for{' '}
              <span className="font-semibold">{searchParams.get('email')}</span>, a code is
              on its way. It can take a minute to arrive.
            </span>
          </p>
        )}
        {resent && (
          <p className="flex items-start gap-2 rounded-xl bg-primary/8 px-3.5 py-2.5 text-sm text-foreground">
            <MailCheck className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden="true" />
            <span>A new code has been sent. Use the most recent one.</span>
          </p>
        )}

        <Field label="Email address" htmlFor="email" required>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
          />
        </Field>

        <Field label="Six digit code" htmlFor="code" required>
          <Input
            id="code"
            // `one-time-code` is what lets a phone offer the code straight from
            // the notification instead of making the student switch apps.
            autoComplete="one-time-code"
            inputMode="numeric"
            pattern="[0-9]*"
            maxLength={CODE_LENGTH}
            required
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
            placeholder="000000"
            className="h-12 text-center font-display text-xl tracking-[0.4em]"
          />
        </Field>

        <Field label="New password" htmlFor="password" required>
          <Input
            id="password"
            type="password"
            autoComplete="new-password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="At least 8 characters, with a letter and a number"
          />
        </Field>

        <Field label="Confirm new password" htmlFor="confirm" required>
          <Input
            id="confirm"
            type="password"
            autoComplete="new-password"
            required
            minLength={8}
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            placeholder="Type it again"
          />
        </Field>

        {error && (
          <p className="rounded-xl bg-destructive/10 px-3.5 py-2.5 text-sm font-medium text-destructive" role="alert">
            {error}
          </p>
        )}

        <Button type="submit" className="w-full" size="lg" loading={loading}>
          <KeyRound /> Reset password
        </Button>

        <Button
          type="button"
          variant="ghost"
          className="w-full"
          onClick={resend}
          loading={resending}
        >
          Send a new code
        </Button>
      </form>
    </AuthLayout>
  )
}
