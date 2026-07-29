import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * Small data-loading hook: runs `fetcher` on mount (and whenever `deps`
 * change), tracks loading/error state and exposes a `reload`.
 *
 * Deliberately tiny — the app has no server-state library, and every page
 * needs the same four things.
 */
export function useFetch(fetcher, deps = [], { enabled = true } = {}) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(enabled)
  const [error, setError] = useState(null)
  const mounted = useRef(true)
  const callbackRef = useRef(fetcher)

  // Kept in an effect rather than assigned during render: a render can be
  // thrown away, and mutating a ref on a discarded render is how you end up
  // fetching with a callback that never committed.
  useEffect(() => {
    callbackRef.current = fetcher
  })

  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
    }
  }, [])

  // `deps` is caller-supplied and of unknown length, which a hook dependency
  // array is not allowed to be. Every call site passes primitives (ids, ISO
  // dates, flags), so serialising them gives a stable literal dependency with
  // the same change detection.
  const depsKey = JSON.stringify(deps ?? [])

  const run = useCallback(
    async (options = {}) => {
      if (!enabled) return null
      if (!options.silent) setLoading(true)
      setError(null)
      try {
        const result = await callbackRef.current()
        if (mounted.current) setData(result)
        return result
      } catch (err) {
        if (mounted.current) setError(err)
        return null
      } finally {
        if (mounted.current) setLoading(false)
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps -- depsKey looks
    // unused to the linter because the fetcher is reached through a ref, but
    // it is the whole mechanism for refetching when a caller's dep changes
    // (e.g. the planner's week navigation). Removing it breaks that.
    [enabled, depsKey],
  )

  useEffect(() => {
    run()
  }, [run])

  return { data, loading, error, reload: run, setData }
}

/** Tracks the pending state of a one-off action (submit, delete, ...). */
export function usePending(initial = false) {
  const [pending, setPending] = useState(initial)
  const wrap = useCallback(async (action) => {
    setPending(true)
    try {
      return await action()
    } finally {
      setPending(false)
    }
  }, [])
  return [pending, wrap, setPending]
}

export default useFetch
