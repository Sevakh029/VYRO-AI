import { describe, expect, it } from "vitest";
import { generateMockIntersectionStates } from "./mockSignals";

describe("mock intersection state generator", () => {
  it("emits contract-shaped states and advances through phases", () => {
    const now = Date.parse("2026-11-24T12:00:00Z");
    const first = generateMockIntersectionStates(["signal-1", "signal-2"], 0, now);
    const nextPhase = generateMockIntersectionStates(["signal-1"], 5, now + 5000);

    expect(first).toHaveLength(2);
    expect(first[0]).toMatchObject({
      topic: "vyro/v1/intersection/state",
      schema_version: "0.2",
      intersection_id: "signal-1",
      phase_id: 0,
      time_in_phase_s: 0,
      detector_counts: {},
      timestamp: new Date(now).toISOString(),
    });
    expect(nextPhase[0].phase_id).toBe(1);
    expect(nextPhase[0].time_in_phase_s).toBe(0);
  });

  it("skips empty signal identifiers", () => {
    expect(generateMockIntersectionStates(["", "  "], 0)).toEqual([]);
  });
});
