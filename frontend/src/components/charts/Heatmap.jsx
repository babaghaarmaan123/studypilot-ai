import { Hint } from '@/components/ui/tooltip'
import { cn, formatMinutes, parseISODate } from '@/lib/utils'

const LEVELS = [
  'bg-muted',
  'bg-indigo-200 dark:bg-indigo-950',
  'bg-indigo-300 dark:bg-indigo-800',
  'bg-indigo-400 dark:bg-indigo-600',
  'bg-indigo-600 dark:bg-indigo-400',
]

function level(minutes) {
  if (!minutes) return 0
  if (minutes < 30) return 1
  if (minutes < 75) return 2
  if (minutes < 150) return 3
  return 4
}

/**
 * GitHub-style study heatmap. `days` is `[{ date, minutes }]` ordered oldest
 * first; the grid is laid out in columns of seven (Monday at the top).
 */
export function StudyHeatmap({ days = [], className }) {
  if (!days.length) return null

  // Pad the start so the first column begins on a Monday.
  const first = parseISODate(days[0].date)
  const padding = (first.getDay() + 6) % 7
  const cells = [...Array.from({ length: padding }, () => null), ...days]

  const columns = []
  for (let i = 0; i < cells.length; i += 7) columns.push(cells.slice(i, i + 7))

  return (
    <div className={cn('w-full', className)}>
      <div className="flex gap-1 overflow-x-auto pb-1">
        {columns.map((column, columnIndex) => (
          <div key={columnIndex} className="flex flex-col gap-1">
            {Array.from({ length: 7 }).map((_, rowIndex) => {
              const day = column[rowIndex]
              if (!day) {
                return <span key={rowIndex} className="size-3 rounded-[3px]" />
              }
              const date = parseISODate(day.date)
              return (
                <Hint
                  key={day.date}
                  label={`${date.toLocaleDateString('en-GB', {
                    weekday: 'short',
                    day: 'numeric',
                    month: 'short',
                  })} · ${day.minutes ? formatMinutes(day.minutes) : 'no study'}`}
                >
                  <span
                    tabIndex={0}
                    className={cn(
                      'size-3 rounded-[3px] transition-transform hover:scale-125 focus-visible:scale-125',
                      LEVELS[level(day.minutes)],
                    )}
                  />
                </Hint>
              )
            })}
          </div>
        ))}
      </div>
      <div className="mt-3 flex items-center justify-end gap-1.5 text-xs text-muted-foreground">
        <span>Less</span>
        {LEVELS.map((cls, index) => (
          <span key={index} className={cn('size-3 rounded-[3px]', cls)} />
        ))}
        <span>More</span>
      </div>
    </div>
  )
}

export default StudyHeatmap
