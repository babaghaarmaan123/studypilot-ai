import { motion } from 'framer-motion'
import { TrendingDown, TrendingUp } from 'lucide-react'

import { Card } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { cn } from '@/lib/utils'

const TONES = {
  indigo: 'from-indigo-500/15 to-violet-500/10 text-indigo-600 dark:text-indigo-300',
  emerald: 'from-emerald-500/15 to-teal-500/10 text-emerald-600 dark:text-emerald-300',
  amber: 'from-amber-500/15 to-orange-500/10 text-amber-600 dark:text-amber-300',
  rose: 'from-rose-500/15 to-pink-500/10 text-rose-600 dark:text-rose-300',
  sky: 'from-sky-500/15 to-cyan-500/10 text-sky-600 dark:text-sky-300',
  violet: 'from-violet-500/15 to-fuchsia-500/10 text-violet-600 dark:text-violet-300',
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
      <Card className={cn('card-hover h-full p-5', className)}>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              {label}
            </p>
            <p className="mt-1.5 font-display text-2xl font-bold tabular-nums sm:text-[26px]">
              {value}
            </p>
          </div>
          {Icon && (
            <span
              className={cn(
                'grid size-10 shrink-0 place-items-center rounded-xl bg-gradient-to-br',
                TONES[tone] || TONES.indigo,
              )}
            >
              <Icon className="size-5" />
            </span>
          )}
        </div>

        {typeof progress === 'number' && (
          <Progress value={progress} className="mt-4 h-1.5" />
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
