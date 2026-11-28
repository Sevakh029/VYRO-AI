import { afterEach, describe, expect, it, vi } from "vitest";
import {
  createInitialDashboardStore,
  dashboardStoreReducer,
  isStale,
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

function acknowledgement(commandId: string) {
  return {
    topic: "vyro/v1/controller/ack",
    schema_version: "0.2",
    command_id: commandId,
    signal_id: "signal-1",
    phase: 2,
    hold_s: 10,
    applied: true,
    reason: "applied",
    ts_utc: "2026-11-24T12:00:00Z",
  };
}

afterEach(() => {
  vi.useRealTimers();
});

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

    expect(fromMessage.vehicles["vehicle-1"].value.vehicle_id).toBe("vehicle-1");
    expect(fromMessage.vehicles["vehicle-1"].lastUpdated).toBe(receivedAt - 1000);
    expect(fromLocalTime.vehicles["vehicle-2"].lastUpdated).toBe(receivedAt);
  });

  it("keeps the latest state per pid and marks it stale on reconnect without duplication", () => {
    const populated = dashboardStoreReducer(receive(vehicle("vehicle-1")), {
      type: "message",
      value: { ...vehicle("vehicle-1"), speed_mps: 9 },
      receivedAt: receivedAt + 100,
    });
    const reconnecting = dashboardStoreReducer(populated, { type: "reconnecting" });

    expect(Object.keys(reconnecting.vehicles)).toEqual(["vehicle-1"]);
    expect(reconnecting.vehicles["vehicle-1"].value.speed_mps).toBe(9);
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

  it("drops malformed messages and increments droppedMessages", () => {
    const store = receive(
      { ...vehicle("bad-vehicle"), speed_mps: "fast" },
    );

    expect(store.vehicles["bad-vehicle"]).toBeUndefined();
    expect(store.droppedMessages).toBe(1);
  });

  it("caps the combined command and acknowledgement history at 100", () => {
    let store = createInitialDashboardStore();
    for (let index = 0; index < 105; index += 1) {
      store = dashboardStoreReducer(store, {
        type: "message",
        value:
          index % 2 === 0
            ? command(`command-${index}`)
            : acknowledgement(`command-${index}`),
        receivedAt,
      });
    }

    store = dashboardStoreReducer(store, {
      type: "message",
      value: acknowledgement("command-104"),
      receivedAt: receivedAt + 1,
    });

    expect(store.commandHistory).toHaveLength(100);
    expect(store.commandHistory.at(-1)?.value.topic).toBe("vyro/v1/controller/ack");
    expect(
      store.commandHistory.filter(
        (item) =>
          item.value.topic === "vyro/v1/controller/ack" &&
          item.value.command_id === "command-104",
      ),
    ).toHaveLength(1);
  });

  it("removes command mocks and ignores later ones after a live command arrives", () => {
    let store = dashboardStoreReducer(createInitialDashboardStore(), {
      type: "message",
      source: "mock",
      value: command("mock-command"),
      receivedAt,
    });
    store = dashboardStoreReducer(store, {
      type: "message",
      value: command("live-command"),
      receivedAt: receivedAt + 1,
    });
    const afterLateMock = dashboardStoreReducer(store, {
      type: "message",
      source: "mock",
      value: command("late-mock-command"),
      receivedAt: receivedAt + 2,
    });

    expect(store.hasLiveCommandData).toBe(true);
    expect(
      store.commandHistory.map((item) => item.value.command_id),
    ).toEqual(["live-command"]);
    expect(afterLateMock.commandHistory).toBe(store.commandHistory);
  });

  it("ignores mock metrics after the first live snapshot arrives", () => {
    const metrics = (vehicleCount: number) => ({
      topic: "vyro/v1/metrics/snapshot",
      schema_version: "0.2",
      vehicle_count: vehicleCount,
      mean_speed_mps: 8,
      stopped_vehicle_count: 1,
      timestamp: "2026-11-24T12:00:00Z",
    });
    let store = dashboardStoreReducer(createInitialDashboardStore(), {
      type: "message",
      source: "mock",
      value: metrics(10),
      receivedAt,
    });
    store = dashboardStoreReducer(store, {
      type: "message",
      value: metrics(20),
      receivedAt: receivedAt + 1,
    });
    const afterLateMock = dashboardStoreReducer(store, {
      type: "message",
      source: "mock",
      value: metrics(30),
      receivedAt: receivedAt + 2,
    });

    expect(store.hasLiveMetricsData).toBe(true);
    expect(store.metrics?.value.vehicle_count).toBe(20);
    expect(afterLateMock.metrics).toBe(store.metrics);
  });

  it("marks entries stale after the threshold using fake time", () => {
    vi.useFakeTimers();
    vi.setSystemTime(receivedAt);
    const store = receive(vehicle("vehicle-1"), Date.now());
    const item = store.vehicles["vehicle-1"];

    expect(isStale(item, Date.now())).toBe(false);
    vi.advanceTimersByTime(STALE_THRESHOLD_MS + 1);
    expect(isStale(item, Date.now())).toBe(true);
  });

  it("removes vehicles after the 15 second TTL using fake time", () => {
    vi.useFakeTimers();
    vi.setSystemTime(receivedAt);
    let store = receive(vehicle("vehicle-1"), Date.now());

    vi.advanceTimersByTime(VEHICLE_STATE_TTL_MS + 1);
    store = dashboardStoreReducer(store, { type: "prune", now: Date.now() });
    expect(
      Object.keys(store.vehicles),
    ).toEqual([]);
  });
});
