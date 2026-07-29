import * as React from 'react'
import * as ProgressPrimitive from '@radix-ui/react-progress'

import { cn, clamp } from '@/lib/utils'

const Progress = React.forwardRef(
  ({ className, value = 0, indicatorClassName, ...props }, ref) => (
    <ProgressPrimitive.Root
      ref={ref}
      value={clamp(value)}
      className={cn(
        'relative h-2 w-full overflow-hidden rounded-full bg-muted',
        className,
      )}
      {...props}
    >
      <ProgressPrimitive.Indicator
        className={cn(
          'h-full w-full flex-1 rounded-full bg-gradient-to-r from-indigo-500 to-violet-500 transition-transform duration-700 ease-out',
          indicatorClassName,
        )}
        style={{ transform: `translateX(-${100 - clamp(value)}%)` }}
      />
    </ProgressPrimitive.Root>
  ),
)
Progress.displayName = ProgressPrimitive.Root.displayName

/** Compact circular progress used on stat cards and countdowns. */
function ProgressRing({
  value = 0,
  size = 56,
  stroke = 6,
  className,
  colour = 'hsl(var(--primary))',
  children,
}) {
  const pct = clamp(value)
  const radius = (size - stroke) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (pct / 100) * circumference

  return (
    <div
      className={cn('relative inline-flex items-center justify-center', className)}
      style={{ width: size, height: size }}
      role="img"
      aria-label={`${Math.round(pct)}% complete`}
    >
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          strokeWidth={stroke}
          className="stroke-muted"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          strokeWidth={stroke}
          strokeLinecap="round"
          stroke={colour}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: 'stroke-dashoffset .8s cubic-bezier(.16,1,.3,1)' }}
        />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center text-xs font-bold">
        {children ?? `${Math.round(pct)}%`}
      </span>
    </div>
  )
}

export { Progress, ProgressRing }
