import { useState } from 'react'
import Header from './components/Header'
import KpiPanel from './components/KpiPanel'
import MapArea from './components/MapArea'
import NetworkActivity from './components/NetworkActivity'
import './App.css'

const ONLINE_VEHICLES = 121
const OFFLINE_VEHICLES = 7
const INITIAL_ALERTS = 4

const VEHICLES = [
  { id: 'VY-1042', x: 22, y: 28, speed: '51 km/h', state: 'moving' },
  { id: 'VY-1188', x: 48, y: 28, speed: '44 km/h', state: 'moving' },
  { id: 'VY-1216', x: 64, y: 40, speed: '0 km/h', state: 'idle' },
  { id: 'VY-1304', x: 32, y: 58, speed: '39 km/h', state: 'moving' },
  { id: 'VY-1411', x: 54, y: 66, speed: '47 km/h', state: 'moving' },
  { id: 'VY-1509', x: 22, y: 66, speed: '0 km/h', state: 'idle' },
]

const SYSTEM_STATUS = {
  label: 'System operational',
  tone: 'ok',
}

function App() {
  const [alertCount, setAlertCount] = useState(INITIAL_ALERTS)

  const metrics = [
    {
      id: 'vehicles',
      label: 'Connected vehicles',
      value: String(ONLINE_VEHICLES + OFFLINE_VEHICLES),
      detail: 'Registered on the sample network',
    },
    {
      id: 'alerts',
      label: 'Active alerts',
      value: String(alertCount),
      detail: 'Includes locally simulated events',
    },
    {
      id: 'speed',
      label: 'Average vehicle speed',
      value: '46 km/h',
      detail: 'Sample fleet average',
    },
  ]

  function handleSimulateAlert() {
    setAlertCount((current) => current + 1)
  }

  return (
    <div className="dashboard">
      <Header status={SYSTEM_STATUS} />
      <main className="dashboard-main">
        <KpiPanel metrics={metrics} />
        <div className="dashboard-grid">
          <MapArea vehicles={VEHICLES} />
          <NetworkActivity
            online={ONLINE_VEHICLES}
            offline={OFFLINE_VEHICLES}
            alertCount={alertCount}
            onSimulateAlert={handleSimulateAlert}
          />
        </div>
      </main>
    </div>
  )
}

export default App
