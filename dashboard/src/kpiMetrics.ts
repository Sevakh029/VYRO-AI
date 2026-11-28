import { isStale, type DashboardStore } from "./store";

export interface KpiSummary {
  source: "metrics" | "vehicle stream" | null;
  vehicleCount: number | null;
  meanSpeedKmh: number | null;
  stoppedVehicleCount: number | null;
  stale: boolean;
  scenarioLabel: string | null;
  seed: string | number | null;
}

function finiteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function optionalLabel(value: unknown): string | null {
  return typeof value === "string" && value.trim().length > 0 ? value : null;
}

function optionalSeed(value: unknown): string | number | null {
  return optionalLabel(value) ?? (finiteNumber(value) ? value : null);
}

export function deriveKpiSummary(
  store: Pick<DashboardStore, "metrics" | "vehicles">,
  now = Date.now(),
): KpiSummary {
  if (store.metrics) {
    const metrics = store.metrics.value;
    return {
      source: "metrics",
      vehicleCount: finiteNumber(metrics.vehicle_count)
        ? metrics.vehicle_count
        : null,
      meanSpeedKmh: finiteNumber(metrics.mean_speed_mps)
        ? metrics.mean_speed_mps * 3.6
        : null,
      stoppedVehicleCount: finiteNumber(metrics.stopped_vehicle_count)
        ? metrics.stopped_vehicle_count
        : null,
      stale: isStale(store.metrics, now),
      scenarioLabel: optionalLabel(metrics.scenario_label),
      seed: optionalSeed(metrics.seed),
    };
  }

  const vehicles = Object.values(store.vehicles);
  if (vehicles.length === 0) {
    return {
      source: null,
      vehicleCount: null,
      meanSpeedKmh: null,
      stoppedVehicleCount: null,
      stale: false,
      scenarioLabel: null,
      seed: null,
    };
  }

  const speeds = vehicles
    .map(({ value }) => value.speed_mps)
    .filter(finiteNumber);
  const meanSpeedMps =
    speeds.length > 0
      ? speeds.reduce((total, speed) => total + speed, 0) / speeds.length
      : null;

  return {
    source: "vehicle stream",
    vehicleCount: vehicles.length,
    meanSpeedKmh:
      meanSpeedMps === null ? null : meanSpeedMps * 3.6,
    stoppedVehicleCount: speeds.filter((speed) => speed < 0.1).length,
    stale: vehicles.some((item) => isStale(item, now)),
    scenarioLabel: null,
    seed: null,
  };
}
