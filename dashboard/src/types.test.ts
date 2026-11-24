import { describe, expect, it } from "vitest";
import {
  messageKey,
  parseTopicMessage,
  pruneStaleVehicleStates,
  VEHICLE_STATE_TTL_MS,
  type TopicMessageStore,
} from "./types";

describe("WebSocket message parsing", () => {
  it("accepts supported topics and keys messages by entity", () => {
    const message = parseTopicMessage({
      topic: "vyro/v1/vehicle/state",
      vehicle_id: "vehicle-1",
      latitude: 40.18,
    });

    expect(message?.topic).toBe("vyro/v1/vehicle/state");
    expect(message && messageKey(message)).toBe("vehicle-1");
  });

  it("rejects unknown topics and malformed values", () => {
    expect(parseTopicMessage({ topic: "vyro/v1/unknown" })).toBeNull();
    expect(parseTopicMessage(null)).toBeNull();
    expect(parseTopicMessage("not json")).toBeNull();
  });

  it("expires stale vehicle positions while preserving other topic messages", () => {
    const now = Date.parse("2026-11-24T12:00:00Z");
    const messages: TopicMessageStore = {
      "vyro/v1/vehicle/state": {
        current: {
          topic: "vyro/v1/vehicle/state",
          vehicle_id: "current",
          timestamp: new Date(now - VEHICLE_STATE_TTL_MS).toISOString(),
        },
        stale: {
          topic: "vyro/v1/vehicle/state",
          vehicle_id: "stale",
          timestamp: new Date(now - VEHICLE_STATE_TTL_MS - 1).toISOString(),
        },
        malformed: {
          topic: "vyro/v1/vehicle/state",
          vehicle_id: "malformed",
        },
      },
      "vyro/v1/metrics/snapshot": {
        metrics: {
          topic: "vyro/v1/metrics/snapshot",
        },
      },
    };

    const pruned = pruneStaleVehicleStates(messages, now);

    expect(Object.keys(pruned["vyro/v1/vehicle/state"] ?? {})).toEqual([
      "current",
    ]);
    expect(pruned["vyro/v1/metrics/snapshot"]).toBe(
      messages["vyro/v1/metrics/snapshot"],
    );
  });
});
