import { clsx } from 'clsx'
import {
  Activity,
  Award,
  BookOpen,
  CalendarClock,
  CheckCircle2,
  CircleCheck,
  FileCheck,
  FileText,
  FileUp,
  Image,
  KeyRound,
  RefreshCw,
  Repeat,
  Sparkles,
  Trash2,
  UserPlus,
  UserRound,
  WandSparkles,
} from 'lucide-react'
import { twMerge } from 'tailwind-merge'

/** Tailwind-aware className combiner. */
export function cn(...inputs) {
  return twMerge(clsx(inputs))
}

// --- Dates ----------------------------------------------------------------

/** `YYYY-MM-DD` in local time (never UTC — that shifts the date near midnight). */
export function toISODate(date) {
  const d = date instanceof Date ? date : new Date(date)
  const month = `${d.getMonth() + 1}`.padStart(2, '0')
  const day = `${d.getDate()}`.padStart(2, '0')
  return `${d.getFullYear()}-${month}-${day}`
}

/** Parse `YYYY-MM-DD` as a local date so it does not drift a day backwards. */
export function parseISODate(value) {
  if (!value) return null
  if (value instanceof Date) return value
  const [y, m, d] = value.split('-').map(Number)
  return new Date(y, (m || 1) - 1, d || 1)
}

export function formatDate(value, options = { day: 'numeric', month: 'short' }) {
  const date = parseISODate(value)
  if (!date) return ''
  return date.toLocaleDateString('en-GB', options)
}

export function formatLongDate(value) {
  return formatDate(value, { weekday: 'long', day: 'numeric', month: 'long' })
}

export function formatTime(value) {
  if (!value) return ''
  return value.slice(0, 5)
}

/** "in 12 days" / "today" / "3 days ago" */
export function relativeDays(days) {
  if (days === 0) return 'today'
  if (days === 1) return 'tomorrow'
  if (days === -1) return 'yesterday'
  if (days > 0) return `in ${days} days`
  return `${Math.abs(days)} days ago`
}

export function daysBetween(from, to) {
  const a = parseISODate(from)
  const b = parseISODate(to)
  if (!a || !b) return 0
  return Math.round((b - a) / 86400000)
}

export function addDays(date, amount) {
  const d = new Date(parseISODate(date))
  d.setDate(d.getDate() + amount)
  return d
}

export function startOfWeek(date = new Date()) {
  const d = new Date(parseISODate(date))
  const diff = (d.getDay() + 6) % 7 // Monday-first
  d.setDate(d.getDate() - diff)
  d.setHours(0, 0, 0, 0)
  return d
}

/** Add minutes to an "HH:MM" string. */
export function addMinutesToTime(time, minutes) {
  const [h, m] = (time || '00:00').split(':').map(Number)
  const total = h * 60 + m + minutes
  const hh = `${Math.floor(total / 60) % 24}`.padStart(2, '0')
  const mm = `${total % 60}`.padStart(2, '0')
  return `${hh}:${mm}`
}

// --- Numbers & text -------------------------------------------------------

export function formatMinutes(minutes) {
  const total = Math.max(0, Math.round(minutes || 0))
  const h = Math.floor(total / 60)
  const m = total % 60
  if (!h) return `${m}m`
  if (!m) return `${h}h`
  return `${h}h ${m}m`
}

export function formatHours(hours) {
  const value = Number(hours || 0)
  return Number.isInteger(value) ? `${value}h` : `${value.toFixed(1)}h`
}

export function clamp(value, min = 0, max = 100) {
  return Math.min(max, Math.max(min, Number(value) || 0))
}

export function pluralise(count, singular, plural) {
  return `${count} ${count === 1 ? singular : plural || `${singular}s`}`
}

export function initials(name) {
  if (!name) return 'S'
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() || '')
    .join('')
}

/** Readable text colour for an arbitrary hex background. */
export function contrastText(hex) {
  if (!hex) return '#fff'
  const clean = hex.replace('#', '')
  const full =
    clean.length === 3
      ? clean
          .split('')
          .map((c) => c + c)
          .join('')
      : clean
  const r = parseInt(full.slice(0, 2), 16)
  const g = parseInt(full.slice(2, 4), 16)
  const b = parseInt(full.slice(4, 6), 16)
  return (r * 299 + g * 587 + b * 114) / 1000 > 150 ? '#0f172a' : '#ffffff'
}

export function hexToRgba(hex, alpha = 1) {
  if (!hex) return `rgba(99,102,241,${alpha})`
  const clean = hex.replace('#', '')
  const full =
    clean.length === 3
      ? clean
          .split('')
          .map((c) => c + c)
          .join('')
      : clean
  const r = parseInt(full.slice(0, 2), 16)
  const g = parseInt(full.slice(2, 4), 16)
  const b = parseInt(full.slice(4, 6), 16)
  return `rgba(${r},${g},${b},${alpha})`
}

// --- Domain labels --------------------------------------------------------

export const CURRICULUM_LABELS = {
  gcse: 'GCSE',
  a_level: 'A Levels',
  international_a_level: 'International A Levels',
}

export const SESSION_KIND_LABELS = {
  study: 'Study',
  revision: 'Revision',
  admission: 'Admissions',
  past_paper: 'Past paper',
  break: 'Break',
}

export const DIFFICULTY_LABELS = {
  1: 'Very easy',
  2: 'Easy',
  3: 'Moderate',
  4: 'Hard',
  5: 'Very hard',
}

/**
 * Icons the backend can name in an activity, notification or achievement.
 *
 * Registered explicitly rather than resolved off the `lucide-react` namespace:
 * a namespace import is not tree-shakeable, so it pulled all ~1,600 icons
 * (4,867 SVG paths, roughly 700 kB) into the entry bundle to serve the
 * seventeen listed here. Add a row when the backend starts sending a new name —
 * `iconFor` falls back to Activity, so a miss degrades rather than breaks.
 */
const BACKEND_ICONS = {
  activity: Activity,
  award: Award,
  'book-open': BookOpen,
  'calendar-clock': CalendarClock,
  'check-circle': CheckCircle2,
  'circle-check': CircleCheck,
  'file-check': FileCheck,
  'file-text': FileText,
  'file-up': FileUp,
  image: Image,
  'key-round': KeyRound,
  'refresh-cw': RefreshCw,
  repeat: Repeat,
  sparkles: Sparkles,
  'trash-2': Trash2,
  'user-plus': UserPlus,
  'user-round': UserRound,
  'wand-sparkles': WandSparkles,
}

const ICON_FALLBACKS = { Activity, Award }

/** Resolves a backend kebab-case icon name (e.g. "book-open") to a component. */
export function iconFor(name, fallback = 'Activity') {
  return BACKEND_ICONS[name] || ICON_FALLBACKS[fallback] || Activity
}

// --- Subject colours -------------------------------------------------------

const SUBJECT_COLOUR_KEYWORDS = [
  [/computer science|information technology/i, '#3b82f6'], // blue
  [/mathematics|mechanics|statistics|decision maths/i, '#8b5cf6'], // purple
  [/biology/i, '#22c55e'], // green
  [/chemistry/i, '#ef4444'], // red
  [/physics/i, '#f59e0b'], // orange
  [/economics|accounting|business/i, '#eab308'], // yellow
  [/psychology/i, '#ec4899'], // pink
]

const FALLBACK_SUBJECT_PALETTE = [
  '#14b8a6', '#06b6d4', '#a855f7', '#0ea5e9', '#f97316', '#6366f1', '#84cc16', '#f43f5e',
]

/** Auto-assigns a pastel-friendly colour by subject name, per the design spec. */
export function colourForSubject(name, index = 0) {
  const match = SUBJECT_COLOUR_KEYWORDS.find(([pattern]) => pattern.test(name || ''))
  if (match) return match[1]
  return FALLBACK_SUBJECT_PALETTE[index % FALLBACK_SUBJECT_PALETTE.length]
}

export const SYLLABUS_STATUS_META = {
  not_uploaded: { label: 'No syllabus uploaded', dot: 'bg-slate-400' },
  pdf_uploaded: { label: 'PDF uploaded', dot: 'bg-amber-500' },
  ready: { label: 'Syllabus ready', dot: 'bg-emerald-500' },
}

export const REVISION_INTERVAL_LABELS = {
  '2d': '2-day recall',
  '7d': '7-day recall',
  '14d': '14-day recall',
  final: 'Final pre-exam pass',
  retry: 'Extra retry',
}
