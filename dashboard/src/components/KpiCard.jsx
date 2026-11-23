function KpiCard({ label, value, detail }) {
  return (
    <article className="card kpi-card">
      <p className="kpi-label">{label}</p>
      <p className="kpi-value">{value}</p>
      <p className="kpi-detail">{detail}</p>
    </article>
  )
}

export default KpiCard
