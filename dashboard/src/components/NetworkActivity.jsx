function NetworkActivity({ online, offline, alertCount, onSimulateAlert }) {
  const rows = [
    { id: 'online', label: 'Online vehicles', value: online },
    { id: 'offline', label: 'Offline vehicles', value: offline },
    { id: 'alerts', label: 'Active alerts', value: alertCount },
  ]

  return (
    <section className="card activity-card" aria-labelledby="activity-heading">
      <div className="panel-heading">
        <h2 id="activity-heading">Network activity</h2>
        <p>Sample fleet status. Alerts can be simulated locally.</p>
      </div>
      <ul className="activity-list">
        {rows.map((row) => (
          <li key={row.id} className={`activity-row activity-${row.id}`}>
            <span>{row.label}</span>
            <strong>{row.value}</strong>
          </li>
        ))}
      </ul>
      <button type="button" className="alert-button" onClick={onSimulateAlert}>
        Simulate new alert
      </button>
    </section>
  )
}

export default NetworkActivity
