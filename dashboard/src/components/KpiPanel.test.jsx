import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import KpiPanel from './KpiPanel'
import { createInitialDashboardStore } from '../store'
import { STALE_THRESHOLD_MS } from '../types'

afterEach(() => {
  cleanup()
  vi.useRealTimers()
})

function renderPanel(store) {
  return render(
    <KpiPanel
      store={store}
      onMockMessage={vi.fn()}
      useMockKpis={false}
    />,
  )
}

describe('KpiPanel', () => {
  it('shows a stale badge when the latest snapshot exceeds the stale threshold', () => {
    vi.useFakeTimers()
    const now = Date.parse('2026-11-24T12:00:00Z')
    vi.setSystemTime(now)
    const store = createInitialDashboardStore()
    store.metrics = {
      value: {
        schema_version: '0.2',
        vehicle_count: 2,
        mean_speed_mps: 4,
        stopped_vehicle_count: 1,
      },
      lastUpdated: now - STALE_THRESHOLD_MS - 1,
      stale: false,
      source: 'live',
    }

    renderPanel(store)

    expect(screen.getAllByText('stale')).toHaveLength(3)
  })

  it('shows placeholders and does not render NaN when no data exists', () => {
    renderPanel(createInitialDashboardStore())

    expect(screen.getAllByText('–')).toHaveLength(3)
    expect(screen.getAllByText('No data')).toHaveLength(3)
    expect(document.body.textContent).not.toContain('NaN')
  })
})
