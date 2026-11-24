function NetworkActivity({ online, offline, alertCount, onSimulateAlert, intersections }) {
  const rows = [
    { id: 'online', label: 'Online vehicles', value: online },
    { id: 'offline', label: 'Offline vehicles', value: offline },
    { id: 'alerts', label: 'Active alerts', value: alertCount },
  ]

  return (
    <section className="card activity-card" aria-labelledby="activity-heading">
      <div className="panel-heading">
        <h2 id="activity-heading">Network activity</h2>
        <p>Live fleet status and observed signal intersections.</p>
      </div>
      <ul className="activity-list">
        {rows.map((row) => (
          <li key={row.id} className={`activity-row activity-${row.id}`}>
            <span>{row.label}</span>
            <strong>{row.value}</strong>
          </li>
        ))}
      </ul>
      {intersections.length > 0 && (
        <ul className="activity-list">
          {intersections.map((intersection) => (
            <li key={intersection.intersection_id} className="activity-row">
              <span>{intersection.intersection_id}</span>
              <strong>Phase {intersection.phase_id}</strong>
            </li>
          ))}
        </ul>
      )}
      <button type="button" className="alert-button" onClick={onSimulateAlert}>
        Simulate new alert
      </button>
    </section>
  )
}

export default NetworkActivity
