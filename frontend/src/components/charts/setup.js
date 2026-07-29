/**
 * One-time Chart.js registration plus theme-aware defaults.
 *
 * Chart.js reads colours at draw time from `Chart.defaults`, so the charts pick
 * up light/dark automatically once `applyChartTheme` runs on a theme change.
 */
import {
  ArcElement,
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Filler,
  Legend,
  LineElement,
  LinearScale,
  PointElement,
  RadialLinearScale,
  Tooltip,
} from 'chart.js'

ChartJS.register(
  CategoryScale,
  LinearScale,
  RadialLinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Filler,
  Tooltip,
  Legend,
)

export function applyChartTheme(isDark) {
  ChartJS.defaults.font.family =
    "Inter, ui-sans-serif, system-ui, -apple-system, sans-serif"
  ChartJS.defaults.font.size = 12
  ChartJS.defaults.color = isDark ? 'rgba(203,213,225,.85)' : 'rgba(71,85,105,.9)'
  ChartJS.defaults.borderColor = isDark ? 'rgba(148,163,184,.16)' : 'rgba(15,23,42,.08)'
  ChartJS.defaults.plugins.tooltip.backgroundColor = isDark ? '#0f172a' : '#111827'
  ChartJS.defaults.plugins.tooltip.padding = 10
  ChartJS.defaults.plugins.tooltip.cornerRadius = 10
  ChartJS.defaults.plugins.tooltip.titleFont = { weight: '600', size: 12 }
  ChartJS.defaults.plugins.tooltip.displayColors = false
  ChartJS.defaults.plugins.legend.labels.usePointStyle = true
  ChartJS.defaults.plugins.legend.labels.boxWidth = 8
  ChartJS.defaults.plugins.legend.labels.padding = 16
  ChartJS.defaults.maintainAspectRatio = false
}

export const BASE_OPTIONS = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: { mode: 'index', intersect: false },
  plugins: { legend: { display: false } },
}

export const PALETTE = [
  '#6366f1',
  '#ec4899',
  '#14b8a6',
  '#f59e0b',
  '#8b5cf6',
  '#06b6d4',
  '#ef4444',
  '#22c55e',
  '#3b82f6',
  '#f97316',
]

export { ChartJS }
