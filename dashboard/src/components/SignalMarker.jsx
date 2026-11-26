import { CircleMarker, Popup, Tooltip } from 'react-leaflet'
import { isStale } from '../store'
import { getSignalId } from './signalId'

const PHASE_COLORS = ['#e5534b', '#3ecfb8', '#f0b429']

export function SignalMarker({
  feature,
  index = 0,
  intersectionsById = {},
  now,
}) {
  const coordinates = feature?.geometry?.coordinates
  if (
    !Array.isArray(coordinates) ||
    !Number.isFinite(coordinates[0]) ||
    !Number.isFinite(coordinates[1])
  ) {
    return null
  }

  const [longitude, latitude] = coordinates
  const signalId = getSignalId(feature, index)
  const tracked =
    intersectionsById[signalId] ??
    Object.values(intersectionsById).find(
      (item) =>
        item?.value?.signal_id === signalId ||
        item?.value?.intersection_id === signalId,
    )
  const state = tracked?.value
  const phase = state?.phase ?? state?.phase_id
  const hasPhase =
    (typeof phase === 'number' && Number.isFinite(phase)) ||
    (typeof phase === 'string' && phase.trim().length > 0)
  const lastUpdatedMs = Number.isFinite(tracked?.lastUpdated)
    ? tracked.lastUpdated
    : null
  const currentTime = Number.isFinite(now) ? now : lastUpdatedMs ?? 0
  const stale =
    !tracked ||
    lastUpdatedMs === null ||
    isStale(tracked, currentTime) ||
    !hasPhase
  const secondsInPhase =
    typeof state?.time_in_phase_s === 'number' &&
    Number.isFinite(state.time_in_phase_s) &&
    state.time_in_phase_s >= 0
      ? state.time_in_phase_s +
        Math.max(
          0,
          Math.floor((currentTime - (lastUpdatedMs ?? currentTime)) / 1000),
        )
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
    stale || !hasPhase ? '#9299a3' : PHASE_COLORS[phaseColorIndex]
  const lastUpdated =
    lastUpdatedMs !== null
      ? new Date(lastUpdatedMs).toLocaleString()
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
