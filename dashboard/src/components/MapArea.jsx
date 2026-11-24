const YEREVAN_BOUNDS = {
  west: Number(import.meta.env.VITE_MAP_WEST || 44.488),
  south: Number(import.meta.env.VITE_MAP_SOUTH || 40.202),
  east: Number(import.meta.env.VITE_MAP_EAST || 44.496),
  north: Number(import.meta.env.VITE_MAP_NORTH || 40.210),
}

function MapArea({ vehicles }) {
  return (
    <section className="card map-card" aria-labelledby="map-heading">
      <div className="panel-heading">
        <h2 id="map-heading">Network map</h2>
        <p>Live vehicle positions within the selected Yerevan network.</p>
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
              key={vehicle.vehicle_id}
              className={`marker marker-${vehicle.speed_mps > 0 ? 'moving' : 'idle'}`}
              style={{
                left: `${Math.max(0, Math.min(100, (vehicle.longitude - YEREVAN_BOUNDS.west) / (YEREVAN_BOUNDS.east - YEREVAN_BOUNDS.west) * 100))}%`,
                top: `${Math.max(0, Math.min(100, (YEREVAN_BOUNDS.north - vehicle.latitude) / (YEREVAN_BOUNDS.north - YEREVAN_BOUNDS.south) * 100))}%`,
              }}
            >
              <span className="marker-dot" aria-hidden="true" />
              <span className="marker-label">
                {vehicle.vehicle_id}
                <span className="marker-meta">{(vehicle.speed_mps * 3.6).toFixed(1)} km/h</span>
              </span>
            </li>
          ))}
        </ul>
        <p className="map-note">Live WebSocket vehicle data and configured Yerevan network bounds.</p>
      </div>
    </section>
  )
}

export default MapArea
