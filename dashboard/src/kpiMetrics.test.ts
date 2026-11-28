import { describe, expect, it } from "vitest";
import {
  createInitialDashboardStore,
  type TrackedItem,
} from "./store";
import type { VehicleState } from "./types";
import { deriveKpiSummary } from "./kpiMetrics";

const now = Date.parse("2026-11-24T12:00:00Z");

function vehicle(speedMps: number): TrackedItem<VehicleState> {
  return {
    value: {
      schema_version: "0.2",
      vehicle_id: `vehicle-${speedMps}`,
      latitude: 40.18,
      longitude: 44.51,
      speed_mps: speedMps,
      heading_deg: 90,
    },
    lastUpdated: now,
    stale: false,
    source: "live",
  };
}

describe("deriveKpiSummary", () => {
  it("computes vehicle count, mean speed, and stopped vehicles from the stream", () => {
    const store = createInitialDashboardStore();
    store.vehicles = {
      first: vehicle(0),
      second: vehicle(0.1),
      third: vehicle(10),
    };

    const summary = deriveKpiSummary(store, now);
    expect(summary).toMatchObject({
      source: "vehicle stream",
      vehicleCount: 3,
      stoppedVehicleCount: 1,
      stale: false,
    });
    expect(summary.meanSpeedKmh).toBeCloseTo(12.12);
  });

  it("uses snapshot values when available and converts mean m/s to km/h", () => {
    const store = createInitialDashboardStore();
    store.metrics = {
      value: {
        schema_version: "0.2",
        vehicle_count: 7,
        mean_speed_mps: 4,
        stopped_vehicle_count: 2,
        scenario_label: "weekday",
        seed: 12,
      },
      lastUpdated: now,
      stale: false,
      source: "live",
    };
    store.vehicles = { ignored: vehicle(20) };

    expect(deriveKpiSummary(store, now)).toMatchObject({
      source: "metrics",
      vehicleCount: 7,
      meanSpeedKmh: 14.4,
      stoppedVehicleCount: 2,
      scenarioLabel: "weekday",
      seed: 12,
    });
  });

  it("returns empty values when neither metrics nor vehicles exist", () => {
    expect(deriveKpiSummary(createInitialDashboardStore(), now)).toMatchObject({
      source: null,
      vehicleCount: null,
      meanSpeedKmh: null,
      stoppedVehicleCount: null,
      stale: false,
    });
  });
});
