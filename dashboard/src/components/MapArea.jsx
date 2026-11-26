import { useEffect, useMemo, useState, useSyncExternalStore } from 'react'
import { CircleMarker, GeoJSON, MapContainer, Popup, TileLayer, Tooltip } from 'react-leaflet'
import { isStale } from '../store'
import { generateMockIntersectionStates } from '../mockSignals'

const CENTER = [40.20408, 44.49249]
const PHASE_COLORS = ['#e5534b', '#3ecfb8', '#f0b429']
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

function getSignalId(feature, index) {
  const id = feature.properties?.tls_id ?? feature.properties?.name
  return typeof id === 'string' && id.trim() ? id : `signal-${index}`
}

function SignalMarker({ feature, index, intersectionsById, now }) {
  const [longitude, latitude] = feature.geometry.coordinates
  const signalId = getSignalId(feature, index)
  const tracked =
    intersectionsById[signalId] ??
    Object.values(intersectionsById).find(
      (item) =>
        item.value.signal_id === signalId ||
        item.value.intersection_id === signalId,
    )
  const state = tracked?.value
  const phase = state?.phase ?? state?.phase_id
  const hasPhase =
    (typeof phase === 'number' && Number.isFinite(phase)) ||
    (typeof phase === 'string' && phase.trim().length > 0)
  const stale = !tracked || isStale(tracked, now) || !hasPhase
  const secondsInPhase =
    typeof state?.time_in_phase_s === 'number' &&
    Number.isFinite(state.time_in_phase_s) &&
    state.time_in_phase_s >= 0
      ? state.time_in_phase_s +
        Math.max(0, Math.floor((now - tracked.lastUpdated) / 1000))
      : null
  const phaseText = hasPhase ? String(phase) : 'No data'
  const timeText =
    secondsInPhase === null ? '—' : `${Math.floor(secondsInPhase)} s`
  const numericPhase =
    typeof phase === 'number' ? phase : Number.parseInt(phaseText, 10)
  const phaseColorIndex = Number.isFinite(numericPhase)
    ? ((Math.trunc(numericPhase) % PHASE_COLORS.length) + PHASE_COLORS.length) %
      PHASE_COLORS.length
    : phaseText.length % PHASE_COLORS.length
  const color =
    stale || !hasPhase
      ? '#9299a3'
      : PHASE_COLORS[phaseColorIndex]
  const lastUpdated =
    tracked && Number.isFinite(tracked.lastUpdated)
      ? new Date(tracked.lastUpdated).toLocaleString()
      : '—'
  const tooltip = stale ? 'No data' : `Phase ${phaseText} · ${timeText}`

  return (
    <CircleMarker
      key={signalId}
      center={[latitude, longitude]}
      radius={8}
      pathOptions={{ color, fillColor: color, fillOpacity: 1, weight: 2 }}
    >
      <Tooltip permanent direction="top" offset={[0, -8]}>
        {tooltip}
      </Tooltip>
      <Popup>
        <strong>{signalId}</strong>
        <br />
        Phase: {stale ? 'No data' : phaseText}
        <br />
        Time in phase: {stale ? 'No data' : timeText}
        <br />
        Last update: {lastUpdated}
      </Popup>
    </CircleMarker>
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
