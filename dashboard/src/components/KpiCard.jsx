function KpiCard({ label, value, unit, detail, stale }) {
  return (
    <article className="card kpi-card">
      <div className="kpi-card-heading">
        <p className="kpi-label">{label}</p>
        {stale && (
          <span className="kpi-stale-badge" aria-label="Data is stale">
            stale
          </span>
        )}
      </div>
      <div className="kpi-value-line">
        <p className="kpi-value">{value}</p>
        <span className="kpi-unit">{unit}</span>
      </div>
      <p className="kpi-detail">{detail}</p>
    </article>
  )
}

export default KpiCard
