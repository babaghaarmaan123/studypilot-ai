import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Mail, MailCheck } from 'lucide-react'

import { AuthLayout } from '@/components/layout/AuthLayout'
import { Button } from '@/components/ui/button'
import { Field } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import api, { ApiError } from '@/lib/api'

export default function ForgotPassword() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [sent, setSent] = useState(false)

  const handleSubmit = async (event) => {
    event.preventDefault()
    setError('')
    setLoading(true)
    try {
      const response = await api.auth.forgotPassword(email)
      setSent(true)
      // In development the backend returns the reset token directly since no
      // mail server is configured — jump straight to the reset screen.
      if (response?.reset_token) {
        setTimeout(() => {
          navigate(`/reset-password?token=${encodeURIComponent(response.reset_token)}`)
        }, 900)
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  if (sent) {
    return (
      <AuthLayout
        title="Check your email"
        subtitle="If an account exists for that address, a reset link is on its way."
      >
        <div className="flex flex-col items-center gap-4 py-4 text-center">
          <span className="grid size-14 place-items-center rounded-2xl bg-emerald-500/15 text-emerald-600 dark:text-emerald-300">
            <MailCheck className="size-7" />
          </span>
          <p className="text-sm text-muted-foreground">
            We sent instructions to <span className="font-semibold text-foreground">{email}</span>.
            It can take a minute to arrive.
          </p>
          <Button variant="outline" asChild className="mt-2 w-full">
            <Link to="/login">Back to login</Link>
          </Button>
        </div>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout
      title="Forgot your password?"
      subtitle="Enter your email and we'll send you a reset link."
      footer={
        <>
          Remembered it?{' '}
          <Link to="/login" className="font-semibold text-primary hover:underline">
            Back to login
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
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

        {error && (
          <p className="rounded-xl bg-destructive/10 px-3.5 py-2.5 text-sm font-medium text-destructive" role="alert">
            {error}
          </p>
        )}

        <Button type="submit" className="w-full" size="lg" loading={loading}>
          <Mail /> Send reset link
        </Button>
      </form>
    </AuthLayout>
  )
}
