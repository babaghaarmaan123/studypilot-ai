import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Mail } from 'lucide-react'

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

  const handleSubmit = async (event) => {
    event.preventDefault()
    setError('')
    setLoading(true)
    try {
      const response = await api.auth.forgotPassword(email)
      /*
       * Straight on to the code screen rather than a "check your email" dead
       * end, because the next thing to do is type the code in. That screen
       * carries the confirmation message instead.
       *
       * The address travels in the query string because the code alone
       * identifies nobody: six digits are not unique across accounts, so the
       * reset endpoint needs the pair.
       */
      const params = new URLSearchParams({ email: email.trim() })
      // Only present when the backend is running in debug with no mail server
      // configured, so local development does not need one.
      if (response?.reset_code) params.set('code', response.reset_code)
      navigate(`/reset-password?${params.toString()}`)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout
      title="Forgot your password?"
      subtitle="Enter your email and we'll send you a six digit code."
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
          <Mail /> Send my code
        </Button>

        <p className="text-center text-xs text-muted-foreground">
          Already have a code?{' '}
          <Link to="/reset-password" className="font-semibold text-primary hover:underline">
            Enter it here
          </Link>
        </p>
      </form>
    </AuthLayout>
  )
}
