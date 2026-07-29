import { cn } from '@/lib/utils'

function Skeleton({ className, ...props }) {
  return <div className={cn('skeleton', className)} {...props} />
}

/** Card-shaped placeholder used while a page's data loads. */
function SkeletonCard({ className, lines = 3 }) {
  return (
    <div
      className={cn(
        'rounded-2xl border border-border/70 bg-card p-5 shadow-card sm:p-6',
        className,
      )}
    >
      <Skeleton className="h-4 w-1/3" />
      <div className="mt-4 space-y-2.5">
        {Array.from({ length: lines }).map((_, i) => (
          <Skeleton
            key={i}
            className="h-3"
            style={{ width: `${92 - i * 14}%` }}
          />
        ))}
      </div>
    </div>
  )
}

function SkeletonStats({ count = 4 }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="rounded-2xl border border-border/70 bg-card p-5 shadow-card"
        >
          <Skeleton className="h-3 w-20" />
          <Skeleton className="mt-3 h-7 w-24" />
          <Skeleton className="mt-3 h-2 w-full" />
        </div>
      ))}
    </div>
  )
}

function SkeletonList({ rows = 5, className }) {
  return (
    <div className={cn('space-y-3', className)}>
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="flex items-center gap-3 rounded-2xl border border-border/70 bg-card p-4"
        >
          <Skeleton className="size-10 shrink-0 rounded-xl" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-3 w-2/5" />
            <Skeleton className="h-3 w-3/5" />
          </div>
          <Skeleton className="h-8 w-20 rounded-lg" />
        </div>
      ))}
    </div>
  )
}

export { Skeleton, SkeletonCard, SkeletonStats, SkeletonList }
