import type { IntersectionState } from "./types";

export interface MockIntersectionState extends IntersectionState {
  topic: "vyro/v1/intersection/state";
  intersection_id: string;
  phase_id: number;
  time_in_phase_s: number;
  detector_counts: Record<string, number>;
  timestamp: string;
}

export function generateMockIntersectionStates(
  signalIds: string[],
  tick: number,
  now = Date.now(),
): MockIntersectionState[] {
  return signalIds
    .filter((signalId) => signalId.trim().length > 0)
    .map((signalId, index) => {
      const phaseOffset = tick + index * 2;
      return {
        topic: "vyro/v1/intersection/state",
        schema_version: "0.2",
        intersection_id: signalId,
        phase_id: Math.floor(phaseOffset / 5) % 3,
        time_in_phase_s: phaseOffset % 5,
        detector_counts: {},
        timestamp: new Date(now).toISOString(),
      };
    });
}
