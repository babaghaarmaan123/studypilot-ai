import { useEffect, useState } from 'react'
import { Check, Loader2 } from 'lucide-react'

import { Card, CardContent } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { cn } from '@/lib/utils'

/*
 * Generating a 28-day plan takes a few seconds on a warm server and longer on a
 * cold one. A spinner inside the button alone left people unsure anything had
 * happened, so this stands in for the plan in the place the plan will appear and
 * narrates the work.
 *
 * The steps are timed, not reported by the server: the endpoint is a single
 * request, so there is no real progress to stream. They are labelled with what
 * the engine genuinely does, in order, and the bar deliberately stops short of
 * 100% until the response actually lands.
 */
const STEPS = [
  'Reading your subjects and exam dates',
  'Scoring what needs the most time',
  'Filling each day around fixed commitments',
  'Booking spaced repetition',
]

export function PlanBuildingPanel() {
  const [step, setStep] = useState(0)

  useEffect(() => {
    const timers = STEPS.map((_, index) =>
      setTimeout(() => setStep(index), index * 900),
    )
    return () => timers.forEach(clearTimeout)
  }, [])

  return (
    <Card className="border-primary/30" aria-live="polite" aria-busy="true">
      <CardContent className="p-5">
        <div className="flex items-center gap-2.5">
          <Loader2 className="size-4 animate-spin text-primary" />
          <p className="font-display text-base font-bold">Building your plan</p>
        </div>

        <Progress
          value={Math.min(92, (step + 1) * 23)}
          className="mt-4 h-1.5"
        />

        <ul className="mt-4 space-y-2">
          {STEPS.map((label, index) => {
            const done = index < step
            const active = index === step
            return (
              <li
                key={label}
                className={cn(
                  'flex items-center gap-2.5 text-sm transition-colors',
                  done && 'text-muted-foreground',
                  active && 'font-medium text-foreground',
                  !done && !active && 'text-muted-foreground/50',
                )}
              >
                <span className="grid size-4 shrink-0 place-items-center">
                  {done ? (
                    <Check className="size-3.5 text-success" />
                  ) : active ? (
                    <Loader2 className="size-3.5 animate-spin text-primary" />
                  ) : (
                    <span className="size-1.5 rounded-full bg-current" />
                  )}
                </span>
                {label}
              </li>
            )
          })}
        </ul>
      </CardContent>
    </Card>
  )
}

export default PlanBuildingPanel
