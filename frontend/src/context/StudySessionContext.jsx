import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'

import { useAuth } from '@/context/AuthContext'
import api from '@/lib/api'
import { parseISODate, toISODate } from '@/lib/utils'

/**
 * Live study-session behaviour, app-wide:
 *
 * * two reminders per session — five minutes before it starts, and again when
 *   it starts
 * * a countdown timer for the session in progress that can be paused
 * * an alarm when the session reaches the time it was scheduled to end
 *
 * Everything is driven by one 1s tick and survives a page reload, so a refresh
 * neither loses a running timer nor replays reminders that already fired.
 */

const StudySessionContext = createContext(null)

const TICK_MS = 1000
const POLL_MS = 60_000
const REMINDER_LEAD_MS = 5 * 60 * 1000
/** How late a reminder may still appear — stops a stale tab firing at midnight. */
const REMINDER_GRACE_MS = 10 * 60 * 1000
/** Starting a session with seconds left shouldn't ring instantly. */
const MIN_TIMER_MS = 60 * 1000

const FIRED_KEY = 'studypilot-session-reminders'
const TIMER_KEY = 'studypilot-session-timer'

/** Absolute start time of a session, in local time. */
export function sessionStartAt(session) {
  const day = parseISODate(session.session_date)
  if (!day) return null
  const [hours, minutes] = (session.start_time || '00:00').split(':').map(Number)
  const at = new Date(day)
  at.setHours(hours || 0, minutes || 0, 0, 0)
  return at
}

export function sessionEndAt(session) {
  const start = sessionStartAt(session)
  if (!start) return null
  return new Date(start.getTime() + (session.duration_minutes || 0) * 60_000)
}

function readJson(key, fallback) {
  try {
    const raw = localStorage.getItem(key)
    return raw ? JSON.parse(raw) : fallback
  } catch {
    return fallback
  }
}

function writeJson(key, value) {
  try {
    if (value === null) localStorage.removeItem(key)
    else localStorage.setItem(key, JSON.stringify(value))
  } catch {
    /* private mode — reminders just won't survive a reload */
  }
}

/**
 * A short repeating chime built with the Web Audio API, so no audio asset has
 * to ship. The context is created on the click that starts a timer, which is
 * the user gesture browsers require before audio may play later.
 */
function useAlarmSound() {
  const contextRef = useRef(null)
  const intervalRef = useRef(null)

  const prepare = useCallback(() => {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext
      if (!AudioCtx) return
      if (!contextRef.current) contextRef.current = new AudioCtx()
      if (contextRef.current.state === 'suspended') contextRef.current.resume()
    } catch {
      /* audio unavailable — the popup alone has to do */
    }
  }, [])

  const beep = useCallback(() => {
    const context = contextRef.current
    if (!context) return
    ;[0, 0.28, 0.56].forEach((offset) => {
      const at = context.currentTime + offset
      const oscillator = context.createOscillator()
      const gain = context.createGain()
      oscillator.type = 'sine'
      oscillator.frequency.setValueAtTime(880, at)
      gain.gain.setValueAtTime(0.0001, at)
      gain.gain.exponentialRampToValueAtTime(0.25, at + 0.02)
      gain.gain.exponentialRampToValueAtTime(0.0001, at + 0.22)
      oscillator.connect(gain).connect(context.destination)
      oscillator.start(at)
      oscillator.stop(at + 0.24)
    })
  }, [])

  const start = useCallback(() => {
    prepare()
    if (intervalRef.current) return
    beep()
    intervalRef.current = setInterval(beep, 2000)
  }, [prepare, beep])

  const stop = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
  }, [])

  useEffect(() => stop, [stop])

  return { prepare, start, stop }
}

export function StudySessionProvider({ children }) {
  const { user, isAuthenticated } = useAuth()
  const remindersOn = user?.settings?.study_reminders !== false

  const [sessions, setSessions] = useState([])
  const [alert, setAlert] = useState(null) // { session, kind: 'soon' | 'start' }
  const [timer, setTimer] = useState(null) // { session, endsAt, remainingMs, paused }
  const [ringing, setRinging] = useState(false)

  const alarm = useAlarmSound()
  // `${sessionId}:${kind}` for every reminder already shown today.
  const firedRef = useRef(new Set())
  const restoredRef = useRef(false)

  // --- Reminder bookkeeping, scoped to today ------------------------------
  useEffect(() => {
    const stored = readJson(FIRED_KEY, null)
    const today = toISODate(new Date())
    firedRef.current = new Set(stored?.date === today ? stored.keys || [] : [])
    if (stored && stored.date !== today) writeJson(FIRED_KEY, null)
  }, [])

  const markFired = useCallback((key) => {
    firedRef.current.add(key)
    writeJson(FIRED_KEY, {
      date: toISODate(new Date()),
      keys: Array.from(firedRef.current),
    })
  }, [])

  // --- Today's sessions ---------------------------------------------------
  const refresh = useCallback(async () => {
    if (!isAuthenticated) return
    try {
      const data = await api.plans.today()
      setSessions(Array.isArray(data) ? data : [])
    } catch {
      /* offline or signed out — keep whatever we had */
    }
  }, [isAuthenticated])

  useEffect(() => {
    if (!isAuthenticated) {
      setSessions([])
      return undefined
    }
    refresh()
    const interval = setInterval(refresh, POLL_MS)
    return () => clearInterval(interval)
  }, [isAuthenticated, refresh])

  // --- Timer -------------------------------------------------------------
  const startTimer = useCallback(
    (session) => {
      const now = Date.now()
      const end = sessionEndAt(session)
      const start = sessionStartAt(session)
      const full = (session.duration_minutes || 30) * 60_000

      // Inside the scheduled window the alarm belongs at the scheduled end;
      // outside it (early, or long after) the student gets the full duration.
      let remainingMs = full
      if (start && end && now >= start.getTime() && now < end.getTime()) {
        remainingMs = Math.max(MIN_TIMER_MS, end.getTime() - now)
      }

      alarm.prepare() // called from a click, so audio is unlocked from here on
      setRinging(false)
      setTimer({ session, endsAt: now + remainingMs, remainingMs, paused: false })
    },
    [alarm],
  )

  const pauseTimer = useCallback(() => {
    setTimer((current) => {
      if (!current || current.paused) return current
      return {
        ...current,
        paused: true,
        remainingMs: Math.max(0, current.endsAt - Date.now()),
        endsAt: null,
      }
    })
  }, [])

  const resumeTimer = useCallback(() => {
    setTimer((current) => {
      if (!current || !current.paused) return current
      return { ...current, paused: false, endsAt: Date.now() + current.remainingMs }
    })
  }, [])

  const stopTimer = useCallback(() => {
    alarm.stop()
    setRinging(false)
    setTimer(null)
    writeJson(TIMER_KEY, null)
  }, [alarm])

  const extendTimer = useCallback(
    (minutes = 5) => {
      alarm.stop()
      setRinging(false)
      setTimer((current) => {
        if (!current) return current
        const extra = minutes * 60_000
        return current.paused
          ? { ...current, remainingMs: current.remainingMs + extra }
          : { ...current, endsAt: Date.now() + extra, remainingMs: extra }
      })
    },
    [alarm],
  )

  const dismissAlarm = stopTimer

  // Restore a timer that was running before a reload.
  useEffect(() => {
    if (restoredRef.current || !sessions.length) return
    restoredRef.current = true
    const stored = readJson(TIMER_KEY, null)
    if (!stored?.sessionId) return
    const session = sessions.find((s) => s.id === stored.sessionId)
    if (!session || session.status !== 'pending') {
      writeJson(TIMER_KEY, null)
      return
    }
    const remainingMs = stored.paused
      ? stored.remainingMs
      : Math.max(0, (stored.endsAt || 0) - Date.now())
    if (remainingMs <= 0) {
      writeJson(TIMER_KEY, null)
      return
    }
    setTimer({
      session,
      paused: Boolean(stored.paused),
      remainingMs,
      endsAt: stored.paused ? null : Date.now() + remainingMs,
    })
  }, [sessions])

  useEffect(() => {
    if (!timer) return
    writeJson(TIMER_KEY, {
      sessionId: timer.session.id,
      endsAt: timer.endsAt,
      remainingMs: timer.remainingMs,
      paused: timer.paused,
    })
  }, [timer])

  // Read by the tick so it never has to re-subscribe when these change.
  const timerRef = useRef(null)
  const alertRef = useRef(null)
  const ringingRef = useRef(false)
  useEffect(() => {
    timerRef.current = timer
  }, [timer])
  useEffect(() => {
    alertRef.current = alert
  }, [alert])
  useEffect(() => {
    ringingRef.current = ringing
  }, [ringing])

  // --- The tick ----------------------------------------------------------
  useEffect(() => {
    const tick = () => {
      const now = Date.now()

      // 1. Countdown and the end-of-session alarm.
      const running = timerRef.current
      if (running && !running.paused) {
        const remainingMs = Math.max(0, (running.endsAt || 0) - now)
        if (remainingMs !== running.remainingMs) {
          setTimer((current) =>
            current && !current.paused ? { ...current, remainingMs } : current,
          )
        }
        if (remainingMs === 0 && running.remainingMs > 0) {
          setRinging(true)
          alarm.start()
        }
      }

      // 2. The two reminders. Never stack a reminder on top of an unanswered
      //    one, on the alarm, or on the session already being timed.
      if (!remindersOn || alertRef.current || ringingRef.current) return
      for (const session of sessions) {
        if (session.status !== 'pending') continue
        if (timerRef.current?.session?.id === session.id) continue
        const start = sessionStartAt(session)
        if (!start) continue
        const startMs = start.getTime()

        const soonKey = `${session.id}:soon`
        if (
          !firedRef.current.has(soonKey) &&
          now >= startMs - REMINDER_LEAD_MS &&
          now < startMs
        ) {
          markFired(soonKey)
          setAlert({ session, kind: 'soon' })
          return
        }

        const startKey = `${session.id}:start`
        if (
          !firedRef.current.has(startKey) &&
          now >= startMs &&
          now < startMs + REMINDER_GRACE_MS
        ) {
          markFired(startKey)
          // The 5-minute warning is moot once the session has begun.
          markFired(soonKey)
          setAlert({ session, kind: 'start' })
          return
        }
      }
    }

    const interval = setInterval(tick, TICK_MS)
    return () => clearInterval(interval)
  }, [sessions, remindersOn, markFired, alarm])

  const dismissAlert = useCallback(() => setAlert(null), [])

  const value = useMemo(
    () => ({
      sessions,
      refresh,
      alert,
      dismissAlert,
      timer,
      ringing,
      startTimer,
      pauseTimer,
      resumeTimer,
      stopTimer,
      extendTimer,
      dismissAlarm,
    }),
    [
      sessions,
      refresh,
      alert,
      dismissAlert,
      timer,
      ringing,
      startTimer,
      pauseTimer,
      resumeTimer,
      stopTimer,
      extendTimer,
      dismissAlarm,
    ],
  )

  return (
    <StudySessionContext.Provider value={value}>{children}</StudySessionContext.Provider>
  )
}

export function useStudySession() {
  const context = useContext(StudySessionContext)
  if (!context) {
    throw new Error('useStudySession must be used inside <StudySessionProvider>')
  }
  return context
}
