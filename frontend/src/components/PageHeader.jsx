import { motion } from 'framer-motion'

import { cn } from '@/lib/utils'

/** Consistent page title block used at the top of every dashboard page. */
export function PageHeader({ title, description, actions, icon: Icon, className }) {
  return (
    <motion.header
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
      className={cn(
        'flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between',
        className,
      )}
    >
      <div className="flex items-start gap-3">
        {Icon && (
          <span className="mt-0.5 grid size-11 shrink-0 place-items-center rounded-2xl bg-primary/10 text-primary">
            <Icon className="size-5" />
          </span>
        )}
        <div className="min-w-0">
          <h1 className="font-display text-2xl font-bold tracking-tight sm:text-[28px]">
            {title}
          </h1>
          {description && (
            <p className="mt-1 text-sm text-muted-foreground">{description}</p>
          )}
        </div>
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </motion.header>
  )
}

export default PageHeader
