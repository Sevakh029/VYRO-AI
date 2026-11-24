import { useEffect, useState } from 'react'
import Header from './components/Header'
import KpiPanel from './components/KpiPanel'
import MapArea from './components/MapArea'
import NetworkActivity from './components/NetworkActivity'
import './App.css'

const INITIAL_ALERTS = 0

function App() {
  const [alertCount, setAlertCount] = useState(INITIAL_ALERTS)
  const [vehicles, setVehicles] = useState({})
  const [connectionStatus, setConnectionStatus] = useState('Connecting')
  const [intersections, setIntersections] = useState({})

  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const backendHost = import.meta.env.VITE_BACKEND_WS_HOST || '127.0.0.1:8000'
    const socket = new WebSocket(`${protocol}//${backendHost}/ws`)

    socket.onopen = () => setConnectionStatus('Live')
    socket.onclose = () => setConnectionStatus('Disconnected')
    socket.onerror = () => setConnectionStatus('Connection error')
    socket.onmessage = (event) => {
      const message = JSON.parse(event.data)
      if (message.vehicle_id) {
        setVehicles((current) => ({
          ...current,
          [message.vehicle_id]: message,
        }))
      }
      if (message.intersection_id) {
        setIntersections((current) => ({
          ...current,
          [message.intersection_id]: message,
        }))
      }
      if (message.advisory_type || message.reason) {
        setAlertCount((current) => current + 1)
      }
    }

    return () => socket.close()
  }, [])

  const vehicleList = Object.values(vehicles)
  const averageSpeed = vehicleList.length
    ? vehicleList.reduce((sum, vehicle) => sum + vehicle.speed_mps, 0) / vehicleList.length
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

  function handleSimulateAlert() {
    setAlertCount((current) => current + 1)
  }

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
            onSimulateAlert={handleSimulateAlert}
            intersections={Object.values(intersections)}
          />
        </div>
      </main>
    </div>
  )
}

export default App
