import { motion } from 'framer-motion'
import { TrendingDown, TrendingUp } from 'lucide-react'

import { Card } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { cn } from '@/lib/utils'

/*
 * Flat tinted chips instead of gradient washes. Tone names are kept so the
 * dozens of call sites do not change, but they now map onto the theme's own
 * colours rather than six unrelated Tailwind ramps.
 */
const TONES = {
  indigo: 'bg-primary/10 text-primary',
  primary: 'bg-primary/10 text-primary',
  emerald: 'bg-success/10 text-success',
  amber: 'bg-accent/15 text-accent-foreground dark:text-accent',
  rose: 'bg-destructive/10 text-destructive',
  sky: 'bg-secondary text-secondary-foreground',
  violet: 'bg-primary/10 text-primary',
}

export function StatCard({
  label,
  value,
  hint,
  icon: Icon,
  tone = 'indigo',
  progress,
  trend,
  delay = 0,
  className,
}) {
  const TrendIcon = trend > 0 ? TrendingUp : TrendingDown
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay, ease: [0.16, 1, 0.3, 1] }}
    >
      {/* Scales down to roughly 160px wide so these can sit two-up on a phone
          without the label wrapping or the number clipping. */}
      <Card className={cn('card-hover h-full p-3.5 sm:p-5', className)}>
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="truncate text-[11px] font-semibold uppercase tracking-wide text-muted-foreground sm:text-xs">
              {label}
            </p>
            <p className="mt-1 font-display text-xl font-bold tabular-nums sm:mt-1.5 sm:text-[26px]">
              {value}
            </p>
          </div>
          {Icon && (
            <span
              className={cn(
                'grid size-8 shrink-0 place-items-center rounded-lg sm:size-10 sm:rounded-xl',
                TONES[tone] || TONES.primary,
              )}
            >
              <Icon className="size-4 sm:size-5" />
            </span>
          )}
        </div>

        {typeof progress === 'number' && (
          <Progress value={progress} className="mt-3 h-1.5 sm:mt-4" />
        )}

        {(hint || typeof trend === 'number') && (
          <div className="mt-3 flex items-center gap-1.5 text-xs text-muted-foreground">
            {typeof trend === 'number' && trend !== 0 && (
              <span
                className={cn(
                  'inline-flex items-center gap-0.5 font-semibold',
                  trend > 0
                    ? 'text-emerald-600 dark:text-emerald-400'
                    : 'text-rose-600 dark:text-rose-400',
                )}
              >
                <TrendIcon className="size-3.5" />
                {Math.abs(trend)}%
              </span>
            )}
            {hint && <span className="truncate">{hint}</span>}
          </div>
        )}
      </Card>
    </motion.div>
  )
}

export default StatCard
