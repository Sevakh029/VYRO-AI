import { useEffect, useState } from 'react'
import KpiCard from './KpiCard'
import { deriveKpiSummary } from '../kpiMetrics'

function formatCount(value) {
  return typeof value === 'number' && Number.isFinite(value)
    ? String(value)
    : '–'
}

function formatSpeed(value) {
  return typeof value === 'number' && Number.isFinite(value)
    ? value.toFixed(1)
    : '–'
}

function KpiPanel({ store, onMockMessage, useMockKpis }) {
  const [now, setNow] = useState(Date.now)
  const summary = deriveKpiSummary(store, now)
  const source = summary.source ? `from ${summary.source}` : 'No data'
  const context = [
    summary.scenarioLabel ? `Scenario: ${summary.scenarioLabel}` : null,
    summary.seed !== null ? `Seed: ${summary.seed}` : null,
  ]
    .filter(Boolean)
    .join(' · ')

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(timer)
  }, [])

  useEffect(() => {
    if (!useMockKpis) return

    const timer = window.setInterval(() => {
      const vehicleCount = Math.floor(Math.random() * 80) + 1
      onMockMessage({
        topic: 'vyro/v1/metrics/snapshot',
        schema_version: '0.2',
        vehicle_count: vehicleCount,
        mean_speed_mps: Math.round(Math.random() * 140) / 10,
        stopped_vehicle_count: Math.floor(
          Math.random() * (vehicleCount + 1),
        ),
        timestamp: new Date().toISOString(),
      })
    }, 1000)

    return () => window.clearInterval(timer)
  }, [onMockMessage, useMockKpis])

  return (
    <section className="kpi-panel" aria-label="Fleet summary">
      <KpiCard
        label="Vehicles"
        value={formatCount(summary.vehicleCount)}
        unit="vehicles"
        detail={source}
        stale={summary.stale}
      />
      <KpiCard
        label="Mean speed"
        value={formatSpeed(summary.meanSpeedKmh)}
        unit="km/h"
        detail={source}
        stale={summary.stale}
      />
      <KpiCard
        label="Stopped vehicles"
        value={formatCount(summary.stoppedVehicleCount)}
        unit="vehicles"
        detail={source}
        stale={summary.stale}
      />
      {context && <p className="kpi-context">{context}</p>}
    </section>
  )
}

export default KpiPanel
