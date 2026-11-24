import KpiCard from './KpiCard'

function KpiPanel({ metrics }) {
  return (
    <section className="kpi-panel" aria-label="Fleet summary">
      {metrics.map((metric) => (
        <KpiCard
          key={metric.id}
          label={metric.label}
          value={metric.value}
          detail={metric.detail}
        />
      ))}
    </section>
  )
}

export default KpiPanel
