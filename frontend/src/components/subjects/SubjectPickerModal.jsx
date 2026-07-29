import { useMemo, useState } from 'react'
import { Check, Search } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'

/**
 * Searchable, multi-select subject picker for the full curriculum subject
 * database. Subjects already on the student's list are shown as "Added" and
 * cannot be re-selected, so duplicates are impossible.
 */
export function SubjectPickerModal({
  open,
  onOpenChange,
  options = [],
  existingNames = [],
  onSubmit,
  loading = false,
}) {
  const [query, setQuery] = useState('')
  const [selected, setSelected] = useState([])

  const existingLower = useMemo(
    () => new Set(existingNames.map((n) => n.toLowerCase())),
    [existingNames],
  )

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return options
    return options.filter((name) => name.toLowerCase().includes(q))
  }, [options, query])

  const toggle = (name) => {
    if (existingLower.has(name.toLowerCase())) return
    setSelected((current) =>
      current.includes(name) ? current.filter((n) => n !== name) : [...current, name],
    )
  }

  const reset = () => {
    setQuery('')
    setSelected([])
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) reset()
        onOpenChange(next)
      }}
    >
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Add subjects</DialogTitle>
          <DialogDescription>
            Search and select every subject you're studying. You can fine-tune
            difficulty, priority and exam board afterwards.
          </DialogDescription>
        </DialogHeader>

        <div className="relative">
          <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search subjects…"
            className="pl-9"
            autoFocus
          />
        </div>

        <div className="max-h-72 space-y-1 overflow-y-auto rounded-xl border border-border/60 p-1.5">
          {filtered.length === 0 && (
            <p className="px-3 py-6 text-center text-sm text-muted-foreground">
              No subjects match "{query}".
            </p>
          )}
          {filtered.map((name) => {
            const already = existingLower.has(name.toLowerCase())
            const checked = already || selected.includes(name)
            return (
              <button
                key={name}
                type="button"
                disabled={already}
                onClick={() => toggle(name)}
                className={cn(
                  'flex w-full items-center justify-between gap-3 rounded-lg px-3 py-2 text-left text-sm transition-colors',
                  already
                    ? 'cursor-not-allowed opacity-50'
                    : checked
                      ? 'bg-primary/10 font-medium text-primary'
                      : 'hover:bg-muted',
                )}
              >
                <span>{name}</span>
                {already ? (
                  <Badge variant="secondary">Added</Badge>
                ) : checked ? (
                  <Check className="size-4 shrink-0" />
                ) : null}
              </button>
            )
          })}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={selected.length === 0}
            loading={loading}
            onClick={async () => {
              await onSubmit(selected)
              reset()
            }}
          >
            Add {selected.length > 0 ? selected.length : ''} subject
            {selected.length === 1 ? '' : 's'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export default SubjectPickerModal
