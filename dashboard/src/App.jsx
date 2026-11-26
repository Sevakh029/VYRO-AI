import { useState } from 'react'
import Header from './components/Header'
import KpiPanel from './components/KpiPanel'
import MapArea from './components/MapArea'
import NetworkActivity from './components/NetworkActivity'
import { useWebSocket } from './useWebSocket'
import './App.css'

function App() {
  const [simulatedAlerts, setSimulatedAlerts] = useState(0)
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const backendHost = import.meta.env.VITE_BACKEND_WS_HOST || '127.0.0.1:8000'
  const { status, store, ingestMockMessage } = useWebSocket(
    `${protocol}//${backendHost}/ws`,
  )
  const connectionStatus =
    status === 'open'
      ? 'Live'
      : status === 'reconnecting'
        ? 'Reconnecting'
        : status === 'closed'
          ? 'Disconnected'
          : 'Connecting'
  const vehicleList = Object.values(store.vehicles).map((item) => item.value)
  const intersections = Object.values(store.intersections).map((item) => item.value)
  const alertCount =
    Object.keys(store.advisories).length + store.commandHistory.length + simulatedAlerts
  const averageSpeed = vehicleList.length
    ? vehicleList.reduce((sum, vehicle) => sum + (vehicle.speed_mps ?? 0), 0) / vehicleList.length
    : 0

  const metrics = [
    {
      id: 'vehicles',
      label: 'Connected vehicles',
      value: String(vehicleList.length),
      detail: 'Received through the live MQTT bridge',
    },
    {
      id: 'alerts',
      label: 'Active alerts',
      value: String(alertCount),
      detail: 'Received advisories and controller alerts',
    },
    {
      id: 'speed',
      label: 'Average vehicle speed',
      value: `${(averageSpeed * 3.6).toFixed(1)} km/h`,
      detail: 'Live fleet average',
    },
  ]

  return (
    <div className="dashboard">
      <Header status={{ label: connectionStatus, tone: status === 'open' ? 'ok' : 'alert' }} />
      <main className="dashboard-main">
        <KpiPanel metrics={metrics} />
        <div className="dashboard-grid">
          <MapArea
            vehicles={vehicleList}
            intersectionsById={store.intersections}
            useMockSignals={
              import.meta.env.VITE_USE_MOCK_SIGNALS === 'true' &&
              !store.hasLiveIntersectionData
            }
            onMockMessage={ingestMockMessage}
          />
          <NetworkActivity
            online={vehicleList.length}
            offline={0}
            alertCount={alertCount}
            onSimulateAlert={() => setSimulatedAlerts((count) => count + 1)}
            intersections={intersections}
          />
        </div>
      </main>
    </div>
  )
}

export default App
