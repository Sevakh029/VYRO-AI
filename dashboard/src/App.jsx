import { useState } from 'react'
import Header from './components/Header'
import KpiPanel from './components/KpiPanel'
import MapArea from './components/MapArea'
import NetworkActivity from './components/NetworkActivity'
import { useWebSocket } from './useWebSocket'
import './App.css'

const VEHICLE_TOPIC = 'vyro/v1/vehicle/state'
const INTERSECTION_TOPIC = 'vyro/v1/intersection/state'
const ADVISORY_TOPIC = 'vyro/v1/vehicle/advisory'
const COMMAND_TOPIC = 'vyro/v1/controller/command'
const ACK_TOPIC = 'vyro/v1/controller/ack'

function App() {
  const [simulatedAlerts, setSimulatedAlerts] = useState(0)
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const backendHost = import.meta.env.VITE_BACKEND_WS_HOST || '127.0.0.1:8000'
  const { status: connectionStatus, messages } = useWebSocket(
    `${protocol}//${backendHost}/ws`,
  )
  const vehicleList = Object.values(messages[VEHICLE_TOPIC] ?? {})
  const intersections = Object.values(messages[INTERSECTION_TOPIC] ?? {})
  const alertCount =
    Object.keys(messages[ADVISORY_TOPIC] ?? {}).length +
    Object.keys(messages[COMMAND_TOPIC] ?? {}).length +
    Object.keys(messages[ACK_TOPIC] ?? {}).length +
    simulatedAlerts
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
      <Header status={{ label: connectionStatus, tone: connectionStatus === 'Live' ? 'ok' : 'alert' }} />
      <main className="dashboard-main">
        <KpiPanel metrics={metrics} />
        <div className="dashboard-grid">
          <MapArea vehicles={vehicleList} />
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
