import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { SignalMarker } from './SignalMarker'

afterEach(() => {
  cleanup()
})

vi.mock('react-leaflet', () => ({
  CircleMarker: ({ children, pathOptions }) => (
    <div data-testid="signal-marker" data-color={pathOptions?.fillColor}>
      {children}
    </div>
  ),
  Popup: ({ children }) => <div data-testid="signal-popup">{children}</div>,
  Tooltip: ({ children }) => <div data-testid="signal-tooltip">{children}</div>,
}))

const now = Date.parse('2026-11-24T12:00:00Z')
const feature = {
  properties: { tls_id: 'signal-1' },
  geometry: { type: 'Point', coordinates: [44.51, 40.18] },
}

function trackedState(overrides = {}) {
  return {
    value: {
      schema_version: '0.2',
      intersection_id: 'signal-1',
      phase_id: 2,
      time_in_phase_s: 15,
      ...overrides,
    },
    lastUpdated: now - 1000,
    stale: false,
    source: 'live',
  }
}

describe('SignalMarker', () => {
  it('renders the current phase and live time in phase', () => {
    render(
      <SignalMarker
        feature={feature}
        intersectionsById={{ 'signal-1': trackedState() }}
        now={now}
      />,
    )

    expect(screen.getByText('Phase 2 · 16 s')).toBeTruthy()
    expect(screen.getByTestId('signal-marker').getAttribute('data-color')).not.toBe(
      '#9299a3',
    )
    expect(screen.getByTestId('signal-popup').textContent).toContain('Last update:')
    expect(screen.getByTestId('signal-popup').textContent).toContain('Time in phase: 16 s')
  })

  it('shows a grey no-data marker when the stored state is stale', () => {
    render(
      <SignalMarker
        feature={feature}
        intersectionsById={{ 'signal-1': trackedState() }}
        now={now + 6000}
      />,
    )

    expect(screen.getByTestId('signal-tooltip').textContent).toBe('No data')
    expect(screen.getByTestId('signal-marker').getAttribute('data-color')).toBe(
      '#9299a3',
    )
    expect(screen.getByTestId('signal-popup').textContent).toContain('Phase: No data')
  })

  it('does not crash when state or signal feature fields are missing', () => {
    const { rerender } = render(
      <SignalMarker
        feature={{
          geometry: { type: 'Point', coordinates: [44.51, 40.18] },
          properties: {},
        }}
        intersectionsById={{ 'signal-0': trackedState({ phase_id: undefined }) }}
        now={now}
      />,
    )

    expect(screen.getByTestId('signal-tooltip').textContent).toBe('No data')

    rerender(<SignalMarker feature={{ properties: {} }} now={now} />)
    expect(screen.queryByTestId('signal-marker')).toBeNull()
  })
})
