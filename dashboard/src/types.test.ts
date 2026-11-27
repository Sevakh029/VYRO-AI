import { describe, expect, it } from "vitest";
import { parseTopicMessage } from "./types";

const vehicleMessage = {
  topic: "vyro/v1/vehicle/state",
  schema_version: "0.2",
  vehicle_id: "vehicle-1",
  latitude: 40.18,
  longitude: 44.51,
  speed_mps: 4,
  heading_deg: 90,
  timestamp: "2026-11-24T12:00:00Z",
};

describe("WebSocket message validation", () => {
  it("accepts contract messages and ignores unknown fields", () => {
    const message = parseTopicMessage({ ...vehicleMessage, future_field: true });

    expect(message?.topic).toBe("vyro/v1/vehicle/state");
    expect(message && "future_field" in message).toBe(true);
  });

  it("accepts canonical and current v0.2 command shapes", () => {
    expect(
      parseTopicMessage({
        topic: "vyro/v1/controller/command",
        schema_version: "0.2",
        command_id: "command-1",
        signal_id: "signal-1",
        phase: 2,
        hold_s: 10,
        reason: "queue_pressure",
        ts_utc: "2026-11-24T12:00:00Z",
      })?.topic,
    ).toBe("vyro/v1/controller/command");
    expect(
      parseTopicMessage({
        topic: "vyro/v1/controller/command",
        schema_version: "0.2",
        command_id: "command-2",
        intersection_id: "intersection-1",
        phase_id: 2,
        reason: "queue_pressure",
        timestamp: "2026-11-24T12:00:00Z",
      })?.topic,
    ).toBe("vyro/v1/controller/command");
  });

  it("validates intersection, acknowledgement, and metrics payloads", () => {
    expect(
      parseTopicMessage({
        topic: "vyro/v1/intersection/state",
        schema_version: "0.2",
        signal_id: "signal-1",
        phase: 2,
        ts_utc: "2026-11-24T12:00:00Z",
      })?.topic,
    ).toBe("vyro/v1/intersection/state");
    expect(
      parseTopicMessage({
        topic: "vyro/v1/controller/ack",
        schema_version: "0.2",
        command_id: "command-1",
        signal_id: "signal-1",
        phase: 2,
        hold_s: 10,
        applied: true,
        reason: "applied",
        ts_utc: "2026-11-24T12:00:00Z",
      })?.topic,
    ).toBe("vyro/v1/controller/ack");
    expect(
      parseTopicMessage({
        topic: "vyro/v1/metrics/snapshot",
        schema_version: "0.2",
        vehicle_count: 2,
        mean_speed_mps: 8,
        stopped_vehicle_count: 1,
      })?.topic,
    ).toBe("vyro/v1/metrics/snapshot");
  });

  it("rejects malformed known messages and unsupported topics", () => {
    expect(parseTopicMessage({ ...vehicleMessage, speed_mps: "fast" })).toBeNull();
    expect(parseTopicMessage({ ...vehicleMessage, topic: "vyro/v1/unknown" })).toBeNull();
    expect(parseTopicMessage(null)).toBeNull();
  });
});
