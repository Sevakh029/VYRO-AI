import { useEffect, useMemo, useState } from 'react'
import { CircleMarker, GeoJSON, MapContainer, Popup, TileLayer } from 'react-leaflet'

const CENTER = [40.20408, 44.49249]

function MapArea({ vehicles }) {
  const [network, setNetwork] = useState(null)

  useEffect(() => {
    let active = true
    fetch('/yerevan_network.geojson')
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Network GeoJSON request failed: ${response.status}`)
        }
        return response.json()
      })
      .then((data) => {
        if (active) setNetwork(data)
      })
      .catch((error) => console.error('Unable to load network GeoJSON', error))

    return () => {
      active = false
    }
  }, [])

  const features = network?.features ?? []
  const roads = useMemo(
    () => ({
      type: 'FeatureCollection',
      features: features.filter((feature) => feature.geometry?.type === 'LineString'),
    }),
    [features],
  )
  const signals = useMemo(
    () => features.filter((feature) => feature.properties?.kind === 'signal'),
    [features],
  )

  return (
    <section className="card map-card" aria-labelledby="map-heading">
      <div className="panel-heading">
        <h2 id="map-heading">Network map</h2>
        <p>Live vehicle positions within the selected Yerevan network.</p>
      </div>
      <div className="map">
        <MapContainer center={CENTER} zoom={14} scrollWheelZoom aria-label="Yerevan network map">
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {roads.features.length > 0 && (
            <GeoJSON
              data={roads}
              style={{ color: '#3ecfb8', weight: 5, opacity: 0.8 }}
            />
          )}
          {signals.map((feature, index) => {
            const [longitude, latitude] = feature.geometry.coordinates
            return (
              <CircleMarker
                key={feature.properties?.name ?? `signal-${index}`}
                center={[latitude, longitude]}
                radius={7}
                pathOptions={{ color: '#f0b429', fillOpacity: 1 }}
              >
                <Popup>{feature.properties?.name ?? 'Traffic signal (sample)'}</Popup>
              </CircleMarker>
            )
          })}
          {vehicles.map((vehicle) => (
            <CircleMarker
              key={vehicle.vehicle_id}
              center={[vehicle.latitude, vehicle.longitude]}
              radius={6}
              pathOptions={{
                color: vehicle.speed_mps > 0 ? '#3ecfb8' : '#f0b429',
                fillOpacity: 0.95,
              }}
            >
              <Popup>
                {vehicle.vehicle_id}: {(vehicle.speed_mps * 3.6).toFixed(1)} km/h
              </Popup>
            </CircleMarker>
          ))}
        </MapContainer>
      </div>
      <p className="map-note">
        Road and signal positions are from the selected OpenStreetMap candidate;{' '}
        <a href="https://www.openstreetmap.org/copyright">© OpenStreetMap contributors</a>{' '}
        (ODbL). The network is not survey-grade.
      </p>
    </section>
  )
}

export default MapArea
