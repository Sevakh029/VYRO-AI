function MapArea({ vehicles }) {
  return (
    <section className="card map-card" aria-labelledby="map-heading">
      <div className="panel-heading">
        <h2 id="map-heading">Network map</h2>
        <p>Sample vehicle positions on an illustrative grid.</p>
      </div>
      <div className="map" role="img" aria-label="Illustrative map with sample vehicle markers">
        <div className="map-surface" aria-hidden="true">
          <span className="road road-h road-h-1" />
          <span className="road road-h road-h-2" />
          <span className="road road-h road-h-3" />
          <span className="road road-v road-v-1" />
          <span className="road road-v road-v-2" />
          <span className="road road-v road-v-3" />
          <span className="block block-a" />
          <span className="block block-b" />
          <span className="block block-c" />
          <span className="block block-d" />
        </div>
        <ul className="markers">
          {vehicles.map((vehicle) => (
            <li
              key={vehicle.id}
              className={`marker marker-${vehicle.state}`}
              style={{ left: `${vehicle.x}%`, top: `${vehicle.y}%` }}
            >
              <span className="marker-dot" aria-hidden="true" />
              <span className="marker-label">
                {vehicle.id}
                <span className="marker-meta">{vehicle.speed}</span>
              </span>
            </li>
          ))}
        </ul>
        <p className="map-note">Illustrative map. Not connected to live vehicle data.</p>
      </div>
    </section>
  )
}

export default MapArea
