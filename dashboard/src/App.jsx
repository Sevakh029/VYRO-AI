import { useState } from 'react'
import Header from './components/Header'
import KpiPanel from './components/KpiPanel'
import MapArea from './components/MapArea'
import NetworkActivity from './components/NetworkActivity'
import { CommandAckPanel } from './components/CommandAckPanel'
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
  return (
    <div className="dashboard">
      <Header status={{ label: connectionStatus, tone: status === 'open' ? 'ok' : 'alert' }} />
      <main className="dashboard-main">
        <KpiPanel
          store={store}
          onMockMessage={ingestMockMessage}
          useMockKpis={
            import.meta.env.VITE_USE_MOCK_KPIS === 'true' &&
            !store.hasLiveMetricsData
          }
        />
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
        <CommandAckPanel
          history={store.commandHistory}
          onMockMessage={ingestMockMessage}
          useMockCommands={
            import.meta.env.VITE_USE_MOCK_COMMANDS === 'true' &&
            !store.hasLiveCommandData
          }
        />
      </main>
    </div>
  )
}

export default App
