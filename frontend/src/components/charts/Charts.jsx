import { useEffect, useMemo } from 'react'
import { Bar, Doughnut, Line, Radar } from 'react-chartjs-2'

import { useTheme } from '@/context/ThemeContext'
import { cn, hexToRgba } from '@/lib/utils'
import { BASE_OPTIONS, PALETTE, applyChartTheme } from './setup'

/** Keeps Chart.js defaults in sync with the active theme. */
function useChartTheme() {
  const { isDark } = useTheme()
  useEffect(() => {
    applyChartTheme(isDark)
  }, [isDark])
  return isDark
}

function ChartFrame({ height = 280, className, children }) {
  return (
    <div className={cn('relative w-full', className)} style={{ height }}>
      {children}
    </div>
  )
}

// ---------------------------------------------------------------------------

export function AreaChart({
  labels,
  values,
  label = 'Hours',
  colour = '#6366f1',
  height,
  suffix = 'h',
  className,
}) {
  useChartTheme()

  const data = useMemo(
    () => ({
      labels,
      datasets: [
        {
          label,
          data: values,
          borderColor: colour,
          backgroundColor: (context) => {
            const { ctx, chartArea } = context.chart
            if (!chartArea) return hexToRgba(colour, 0.18)
            const gradient = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom)
            gradient.addColorStop(0, hexToRgba(colour, 0.32))
            gradient.addColorStop(1, hexToRgba(colour, 0))
            return gradient
          },
          fill: true,
          tension: 0.38,
          borderWidth: 2.5,
          pointRadius: 0,
          pointHoverRadius: 5,
          pointBackgroundColor: colour,
          pointBorderColor: '#fff',
          pointBorderWidth: 2,
        },
      ],
    }),
    [labels, values, label, colour],
  )

  const options = useMemo(
    () => ({
      ...BASE_OPTIONS,
      plugins: {
        ...BASE_OPTIONS.plugins,
        tooltip: {
          callbacks: { label: (item) => `${item.formattedValue}${suffix}` },
        },
      },
      scales: {
        x: { grid: { display: false }, border: { display: false } },
        y: {
          beginAtZero: true,
          border: { display: false },
          grid: { color: 'rgba(148,163,184,.16)' },
          ticks: { callback: (value) => `${value}${suffix}`, maxTicksLimit: 5 },
        },
      },
    }),
    [suffix],
  )

  return (
    <ChartFrame height={height} className={className}>
      <Line data={data} options={options} />
    </ChartFrame>
  )
}

// ---------------------------------------------------------------------------

export function ColumnChart({
  labels,
  values,
  colours,
  label = 'Hours',
  suffix = 'h',
  height,
  horizontal = false,
  max,
  className,
}) {
  useChartTheme()

  const data = useMemo(
    () => ({
      labels,
      datasets: [
        {
          label,
          data: values,
          backgroundColor: colours || labels.map((_, i) => hexToRgba(PALETTE[i % PALETTE.length], 0.85)),
          borderRadius: 8,
          borderSkipped: false,
          maxBarThickness: horizontal ? 22 : 44,
        },
      ],
    }),
    [labels, values, colours, label, horizontal],
  )

  const valueAxis = {
    beginAtZero: true,
    max,
    border: { display: false },
    grid: { color: 'rgba(148,163,184,.16)' },
    ticks: { callback: (value) => `${value}${suffix}`, maxTicksLimit: 5 },
  }
  const categoryAxis = { grid: { display: false }, border: { display: false } }

  const options = useMemo(
    () => ({
      ...BASE_OPTIONS,
      indexAxis: horizontal ? 'y' : 'x',
      plugins: {
        ...BASE_OPTIONS.plugins,
        tooltip: { callbacks: { label: (item) => `${item.formattedValue}${suffix}` } },
      },
      scales: horizontal
        ? { x: valueAxis, y: categoryAxis }
        : { x: categoryAxis, y: valueAxis },
    }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [horizontal, suffix, max],
  )

  return (
    <ChartFrame height={height} className={className}>
      <Bar data={data} options={options} />
    </ChartFrame>
  )
}

// ---------------------------------------------------------------------------

export function DonutChart({ labels, values, colours, height = 260, suffix = 'h', className }) {
  useChartTheme()

  const data = useMemo(
    () => ({
      labels,
      datasets: [
        {
          data: values,
          backgroundColor: colours || labels.map((_, i) => PALETTE[i % PALETTE.length]),
          borderWidth: 0,
          hoverOffset: 8,
          spacing: 2,
        },
      ],
    }),
    [labels, values, colours],
  )

  const options = useMemo(
    () => ({
      ...BASE_OPTIONS,
      cutout: '66%',
      plugins: {
        legend: { display: true, position: 'bottom' },
        tooltip: {
          displayColors: true,
          callbacks: { label: (item) => ` ${item.label}: ${item.formattedValue}${suffix}` },
        },
      },
    }),
    [suffix],
  )

  return (
    <ChartFrame height={height} className={className}>
      <Doughnut data={data} options={options} />
    </ChartFrame>
  )
}

// ---------------------------------------------------------------------------

export function RadarChart({ labels, values, colour = '#8b5cf6', height = 300, className }) {
  useChartTheme()

  const data = useMemo(
    () => ({
      labels,
      datasets: [
        {
          label: 'Readiness',
          data: values,
          backgroundColor: hexToRgba(colour, 0.22),
          borderColor: colour,
          borderWidth: 2,
          pointBackgroundColor: colour,
          pointRadius: 3.5,
        },
      ],
    }),
    [labels, values, colour],
  )

  const options = useMemo(
    () => ({
      ...BASE_OPTIONS,
      scales: {
        r: {
          beginAtZero: true,
          max: 100,
          angleLines: { color: 'rgba(148,163,184,.2)' },
          grid: { color: 'rgba(148,163,184,.2)' },
          pointLabels: { font: { size: 11, weight: '600' } },
          ticks: { display: false, stepSize: 25 },
        },
      },
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: (item) => `${item.formattedValue}% ready` } },
      },
    }),
    [],
  )

  return (
    <ChartFrame height={height} className={className}>
      <Radar data={data} options={options} />
    </ChartFrame>
  )
}

// ---------------------------------------------------------------------------

export function MultiLineChart({ labels, datasets, height, suffix = '%', className }) {
  useChartTheme()

  const data = useMemo(
    () => ({
      labels,
      datasets: datasets.map((set, index) => ({
        label: set.label,
        data: set.values,
        borderColor: set.colour || PALETTE[index % PALETTE.length],
        backgroundColor: hexToRgba(set.colour || PALETTE[index % PALETTE.length], 0.12),
        tension: 0.35,
        borderWidth: 2.5,
        pointRadius: 3,
        pointHoverRadius: 6,
        fill: datasets.length === 1,
      })),
    }),
    [labels, datasets],
  )

  const options = useMemo(
    () => ({
      ...BASE_OPTIONS,
      plugins: {
        legend: { display: datasets.length > 1, position: 'bottom' },
        tooltip: {
          displayColors: true,
          callbacks: { label: (item) => ` ${item.dataset.label}: ${item.formattedValue}${suffix}` },
        },
      },
      scales: {
        x: { grid: { display: false }, border: { display: false } },
        y: {
          beginAtZero: true,
          border: { display: false },
          grid: { color: 'rgba(148,163,184,.16)' },
          ticks: { callback: (value) => `${value}${suffix}`, maxTicksLimit: 6 },
        },
      },
    }),
    [datasets.length, suffix],
  )

  return (
    <ChartFrame height={height} className={className}>
      <Line data={data} options={options} />
    </ChartFrame>
  )
}
