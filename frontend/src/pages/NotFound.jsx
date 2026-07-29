import { Link } from 'react-router-dom'
import { Compass } from 'lucide-react'

import { Button } from '@/components/ui/button'

export default function NotFound() {
  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-background px-4 text-center">
      <div className="pastel-mesh pointer-events-none absolute inset-0 -z-10" aria-hidden="true" />
      <div>
        <span className="mx-auto grid size-16 place-items-center rounded-3xl bg-primary text-primary-foreground">
          <Compass className="size-8" />
        </span>
        <h1 className="mt-6 font-display text-4xl font-bold tracking-tight">404</h1>
        <p className="mt-2 text-muted-foreground">
          This page does not exist.
        </p>
        <Button className="mt-6" asChild>
          <Link to="/dashboard">Back to dashboard</Link>
        </Button>
      </div>
    </div>
  )
}
