import { describe, expect, it } from "vitest";
import {
  createInitialDashboardStore,
  dashboardStoreReducer,
  isStale,
  pruneExpiredVehicles,
} from "./store";
import { STALE_THRESHOLD_MS, VEHICLE_STATE_TTL_MS } from "./types";

const receivedAt = Date.parse("2026-11-24T12:00:00Z");

function vehicle(vehicleId: string, timestamp?: string) {
  return {
    topic: "vyro/v1/vehicle/state",
    schema_version: "0.2",
    vehicle_id: vehicleId,
    latitude: 40.18,
    longitude: 44.51,
    speed_mps: 4,
    heading_deg: 90,
    ...(timestamp ? { ts_utc: timestamp } : {}),
  };
}

function command(commandId: string) {
  return {
    topic: "vyro/v1/controller/command",
    schema_version: "0.2",
    command_id: commandId,
    signal_id: "signal-1",
    phase: 2,
    hold_s: 10,
    reason: "queue_pressure",
    ts_utc: "2026-11-24T12:00:00Z",
  };
}

function receive(value: unknown, now = receivedAt) {
  return dashboardStoreReducer(createInitialDashboardStore(), {
    type: "message",
    value,
    receivedAt: now,
  });
}

describe("dashboard store", () => {
  it("uses message timestamps and falls back to local receive time", () => {
    const fromMessage = receive(vehicle("vehicle-1", "2026-11-24T11:59:59Z"));
    const fromLocalTime = receive(vehicle("vehicle-2"));

    expect(fromMessage.vehicles["vehicle-1"].lastUpdated).toBe(receivedAt - 1000);
    expect(fromLocalTime.vehicles["vehicle-2"].lastUpdated).toBe(receivedAt);
  });

  it("marks retained snapshots stale during reconnect and clears the flag on update", () => {
    const populated = receive(vehicle("vehicle-1"));
    const reconnecting = dashboardStoreReducer(populated, { type: "reconnecting" });

    expect(reconnecting.vehicles["vehicle-1"].value.vehicle_id).toBe("vehicle-1");
    expect(isStale(reconnecting.vehicles["vehicle-1"], receivedAt)).toBe(true);

    const recovered = dashboardStoreReducer(reconnecting, {
      type: "message",
      value: vehicle("vehicle-1"),
      receivedAt: receivedAt + 100,
    });
    expect(isStale(recovered.vehicles["vehicle-1"], receivedAt + 100)).toBe(false);
  });

  it("indexes intersections by signal and retains the latest metrics snapshot", () => {
    let store = dashboardStoreReducer(createInitialDashboardStore(), {
      type: "message",
      value: {
        topic: "vyro/v1/intersection/state",
        schema_version: "0.2",
        signal_id: "signal-1",
        phase: 2,
      },
      receivedAt,
    });
    store = dashboardStoreReducer(store, {
      type: "message",
      value: {
        topic: "vyro/v1/metrics/snapshot",
        schema_version: "0.2",
        vehicle_count: 2,
        mean_speed_mps: 8,
        stopped_vehicle_count: 1,
      },
      receivedAt,
    });

    expect(store.intersections["signal-1"].value.phase).toBe(2);
    expect(store.metrics?.value.vehicle_count).toBe(2);
  });

  it("removes mock intersections and ignores later mocks after live data arrives", () => {
    let store = dashboardStoreReducer(createInitialDashboardStore(), {
      type: "message",
      source: "mock",
      value: {
        topic: "vyro/v1/intersection/state",
        schema_version: "0.2",
        intersection_id: "mock-signal",
        phase_id: 1,
        time_in_phase_s: 2,
        detector_counts: {},
        timestamp: "2026-11-24T12:00:00Z",
      },
      receivedAt,
    });
    store = dashboardStoreReducer(store, {
      type: "message",
      value: {
        topic: "vyro/v1/intersection/state",
        schema_version: "0.2",
        intersection_id: "live-signal",
        phase_id: 2,
        time_in_phase_s: 1,
        detector_counts: {},
        timestamp: "2026-11-24T12:00:01Z",
      },
      receivedAt: receivedAt + 1000,
    });
    const afterLateMock = dashboardStoreReducer(store, {
      type: "message",
      source: "mock",
      value: {
        topic: "vyro/v1/intersection/state",
        schema_version: "0.2",
        intersection_id: "late-mock",
        phase_id: 0,
        time_in_phase_s: 0,
        detector_counts: {},
        timestamp: "2026-11-24T12:00:02Z",
      },
      receivedAt: receivedAt + 2000,
    });

    expect(store.hasLiveIntersectionData).toBe(true);
    expect(Object.keys(store.intersections)).toEqual(["live-signal"]);
    expect(afterLateMock.intersections).toBe(store.intersections);
  });

  it("deduplicates command entries, caps history, and counts malformed messages", () => {
    let store = createInitialDashboardStore();
    for (let index = 0; index < 105; index += 1) {
      store = dashboardStoreReducer(store, {
        type: "message",
        value: command(`command-${index}`),
        receivedAt,
      });
    }

    store = dashboardStoreReducer(store, {
      type: "message",
      value: command("command-104"),
      receivedAt: receivedAt + 1,
    });
    store = dashboardStoreReducer(store, {
      type: "message",
      value: { ...vehicle("bad-vehicle"), speed_mps: "fast" },
      receivedAt,
    });

    expect(store.commandHistory).toHaveLength(100);
    expect(store.commandHistory.at(-1)?.value.command_id).toBe("command-104");
    expect(store.commandHistory.filter((item) => item.value.command_id === "command-104"))
      .toHaveLength(1);
    expect(store.droppedMessages).toBe(1);
  });

  it("ages entries by the configured thresholds and prunes old vehicles", () => {
    const store = receive(vehicle("vehicle-1"));
    const item = store.vehicles["vehicle-1"];

    expect(isStale(item, receivedAt + STALE_THRESHOLD_MS)).toBe(false);
    expect(isStale(item, receivedAt + STALE_THRESHOLD_MS + 1)).toBe(true);
    expect(
      Object.keys(
        pruneExpiredVehicles(store, receivedAt + VEHICLE_STATE_TTL_MS + 1).vehicles,
      ),
    ).toEqual([]);
  });
});
