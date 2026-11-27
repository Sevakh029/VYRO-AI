import { useEffect, useMemo, useState, useSyncExternalStore } from 'react'
import { CircleMarker, GeoJSON, MapContainer, Popup, TileLayer } from 'react-leaflet'
import { SignalMarker } from './SignalMarker'
import { getSignalId } from './signalId'
import { generateMockIntersectionStates } from '../mockSignals'

const CENTER = [40.20408, 44.49249]
let clockNow = Date.now()
let clockTimer
const clockSubscribers = new Set()

function getClockSnapshot() {
  return clockNow
}

function subscribeToClock(subscriber) {
  clockSubscribers.add(subscriber)
  if (clockSubscribers.size === 1) {
    clockNow = Date.now()
    clockTimer = window.setInterval(() => {
      clockNow = Date.now()
      clockSubscribers.forEach((notify) => notify())
    }, 1000)
    subscriber()
  }

  return () => {
    clockSubscribers.delete(subscriber)
    if (clockSubscribers.size === 0) {
      window.clearInterval(clockTimer)
      clockTimer = undefined
    }
  }
}

function isSignalFeature(feature) {
  const coordinates = feature?.geometry?.coordinates
  return (
    feature?.properties?.kind === 'signal' &&
    feature.geometry?.type === 'Point' &&
    Array.isArray(coordinates) &&
    Number.isFinite(coordinates[0]) &&
    Number.isFinite(coordinates[1])
  )
}

function MapArea({
  vehicles = [],
  intersectionsById = {},
  useMockSignals = false,
  onMockMessage,
}) {
  const [network, setNetwork] = useState(null)
  const now = useSyncExternalStore(
    subscribeToClock,
    getClockSnapshot,
    getClockSnapshot,
  )

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

  const features = useMemo(
    () => (Array.isArray(network?.features) ? network.features : []),
    [network],
  )
  const roads = useMemo(
    () => ({
      type: 'FeatureCollection',
      features: features.filter((feature) => feature.geometry?.type === 'LineString'),
    }),
    [features],
  )
  const signals = useMemo(
    () => features.filter(isSignalFeature),
    [features],
  )
  const signalIds = useMemo(
    () => signals.map((feature, index) => getSignalId(feature, index)),
    [signals],
  )

  useEffect(() => {
    if (!useMockSignals || !onMockMessage || signalIds.length === 0) return

    let tick = 0
    const emit = () => {
      const messages = generateMockIntersectionStates(signalIds, tick, Date.now())
      tick += 1
      messages.forEach(onMockMessage)
    }

    emit()
    const timer = window.setInterval(emit, 1000)
    return () => window.clearInterval(timer)
  }, [onMockMessage, signalIds, useMockSignals])

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
          {signals.map((feature, index) => (
            <SignalMarker
              key={getSignalId(feature, index)}
              feature={feature}
              index={index}
              intersectionsById={intersectionsById}
              now={now}
            />
          ))}
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
