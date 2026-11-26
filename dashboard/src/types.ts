export type WebSocketTopic =
  | "vyro/v1/vehicle/state"
  | "vyro/v1/intersection/state"
  | "vyro/v1/controller/command"
  | "vyro/v1/controller/ack"
  | "vyro/v1/vehicle/advisory"
  | "vyro/v1/metrics/snapshot"
  | "vyro/v1/preemption/request";

interface TimestampFields {
  schema_version: string;
  ts_utc?: string;
  timestamp?: string;
  [key: string]: unknown;
}

export interface VehicleState extends TimestampFields {
  vehicle_id: string;
  latitude: number;
  longitude: number;
  speed_mps: number;
  heading_deg: number;
  vehicle_type?: "car" | "minibus" | "truck" | "emergency" | "unknown";
}

export interface IntersectionState extends TimestampFields {
  signal_id?: string;
  intersection_id?: string;
  phase?: string | number;
  phase_id?: string | number;
  time_in_phase_s?: number;
  detector_counts?: Record<string, number>;
}

interface SignalIdentity {
  command_id: string;
  reason: string;
}

export interface SignalCommand extends TimestampFields, SignalIdentity {
  signal_id: string;
  phase: string | number;
  hold_s: number;
  ts_utc: string;
}

export interface LegacySignalCommand extends TimestampFields, SignalIdentity {
  intersection_id: string;
  phase_id: string | number;
  hold_s?: number;
}

export interface ControllerAck extends TimestampFields, SignalIdentity {
  command_id: string;
  signal_id: string;
  phase: string | number;
  hold_s: number;
  applied: boolean;
  ts_utc: string;
}

export interface LegacyControllerAck extends TimestampFields, SignalIdentity {
  command_id: string;
  intersection_id: string;
  phase_id?: string | number;
  hold_s?: number;
  applied: boolean;
}

export interface MetricsSnapshot extends TimestampFields {
  vehicle_count: number;
  mean_speed_mps: number;
  stopped_vehicle_count: number;
}

export interface AuxiliaryTopicMessage {
  topic: "vyro/v1/vehicle/advisory" | "vyro/v1/preemption/request";
  vehicle_id?: string;
  command_id?: string;
  ts_utc?: string;
  timestamp?: string;
  [key: string]: unknown;
}

export type CommandMessage =
  | (SignalCommand & { topic: "vyro/v1/controller/command" })
  | (LegacySignalCommand & { topic: "vyro/v1/controller/command" });

export type AckMessage =
  | (ControllerAck & { topic: "vyro/v1/controller/ack" })
  | (LegacyControllerAck & { topic: "vyro/v1/controller/ack" });

export type DashboardMessage =
  | (VehicleState & { topic: "vyro/v1/vehicle/state" })
  | (IntersectionState & { topic: "vyro/v1/intersection/state" })
  | CommandMessage
  | AckMessage
  | (MetricsSnapshot & { topic: "vyro/v1/metrics/snapshot" })
  | AuxiliaryTopicMessage;

export type WebSocketStatus = "connecting" | "open" | "reconnecting" | "closed";

export const STALE_THRESHOLD_MS = 5_000;
export const VEHICLE_STATE_TTL_MS = 15_000;

const WEB_SOCKET_TOPICS: readonly WebSocketTopic[] = [
  "vyro/v1/vehicle/state",
  "vyro/v1/intersection/state",
  "vyro/v1/controller/command",
  "vyro/v1/controller/ack",
  "vyro/v1/vehicle/advisory",
  "vyro/v1/metrics/snapshot",
  "vyro/v1/preemption/request",
];

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function isWebSocketTopic(value: unknown): value is WebSocketTopic {
  return (
    typeof value === "string" &&
    WEB_SOCKET_TOPICS.some((topic) => topic === value)
  );
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function isValidTimestamp(value: unknown): boolean {
  return (
    typeof value === "string" &&
    value.endsWith("Z") &&
    Number.isFinite(Date.parse(value))
  );
}

function hasValidTimestampFields(value: Record<string, unknown>): boolean {
  return (
    typeof value.schema_version === "string" &&
    (value.ts_utc === undefined || isValidTimestamp(value.ts_utc)) &&
    (value.timestamp === undefined || isValidTimestamp(value.timestamp))
  );
}

function isVehicleState(
  value: Record<string, unknown>,
): value is VehicleState & { topic: "vyro/v1/vehicle/state" } {
  return (
    value.topic === "vyro/v1/vehicle/state" &&
    hasValidTimestampFields(value) &&
    isNonEmptyString(value.vehicle_id) &&
    isFiniteNumber(value.latitude) &&
    isFiniteNumber(value.longitude) &&
    isFiniteNumber(value.speed_mps) &&
    isFiniteNumber(value.heading_deg) &&
    (value.vehicle_type === undefined ||
      ["car", "minibus", "truck", "emergency", "unknown"].some(
        (vehicleType) => vehicleType === value.vehicle_type,
      ))
  );
}

function isIntersectionState(
  value: Record<string, unknown>,
): value is IntersectionState & { topic: "vyro/v1/intersection/state" } {
  const hasIdentity =
    isNonEmptyString(value.signal_id) ||
    isNonEmptyString(value.intersection_id);
  const hasPhase =
    isNonEmptyString(value.phase) ||
    isFiniteNumber(value.phase) ||
    isNonEmptyString(value.phase_id) ||
    isFiniteNumber(value.phase_id);
  const counts = value.detector_counts;

  return (
    value.topic === "vyro/v1/intersection/state" &&
    hasValidTimestampFields(value) &&
    hasIdentity &&
    hasPhase &&
    (value.time_in_phase_s === undefined ||
      isFiniteNumber(value.time_in_phase_s)) &&
    (counts === undefined ||
      (isRecord(counts) && Object.values(counts).every(isFiniteNumber)))
  );
}

function isSignalCommand(
  value: Record<string, unknown>,
): value is CommandMessage {
  const canonical = value.signal_id !== undefined || value.phase !== undefined;
  const identity = canonical
    ? isNonEmptyString(value.signal_id) &&
      (isNonEmptyString(value.phase) || isFiniteNumber(value.phase)) &&
      isFiniteNumber(value.hold_s) &&
      value.hold_s > 0 &&
      isValidTimestamp(value.ts_utc)
    : isNonEmptyString(value.intersection_id) &&
      (isNonEmptyString(value.phase_id) || isFiniteNumber(value.phase_id));

  return (
    value.topic === "vyro/v1/controller/command" &&
    hasValidTimestampFields(value) &&
    isNonEmptyString(value.command_id) &&
    isNonEmptyString(value.reason) &&
    identity &&
    (value.hold_s === undefined ||
      (isFiniteNumber(value.hold_s) && value.hold_s > 0))
  );
}

function isControllerAck(
  value: Record<string, unknown>,
): value is AckMessage {
  const canonical = value.signal_id !== undefined || value.phase !== undefined;
  const identity = canonical
    ? isNonEmptyString(value.signal_id) &&
      (isNonEmptyString(value.phase) || isFiniteNumber(value.phase)) &&
      isFiniteNumber(value.hold_s) &&
      value.hold_s > 0 &&
      isValidTimestamp(value.ts_utc)
    : isNonEmptyString(value.intersection_id) &&
      (value.phase_id === undefined ||
        isNonEmptyString(value.phase_id) ||
        isFiniteNumber(value.phase_id));

  return (
    value.topic === "vyro/v1/controller/ack" &&
    hasValidTimestampFields(value) &&
    isNonEmptyString(value.command_id) &&
    isNonEmptyString(value.reason) &&
    typeof value.applied === "boolean" &&
    identity &&
    (value.hold_s === undefined ||
      (isFiniteNumber(value.hold_s) && value.hold_s > 0))
  );
}

function isMetricsSnapshot(
  value: Record<string, unknown>,
): value is MetricsSnapshot & { topic: "vyro/v1/metrics/snapshot" } {
  return (
    value.topic === "vyro/v1/metrics/snapshot" &&
    hasValidTimestampFields(value) &&
    isFiniteNumber(value.vehicle_count) &&
    isFiniteNumber(value.mean_speed_mps) &&
    isFiniteNumber(value.stopped_vehicle_count)
  );
}

function isAuxiliaryTopicMessage(
  value: Record<string, unknown>,
): value is Record<string, unknown> & AuxiliaryTopicMessage {
  return (
    (value.topic === "vyro/v1/vehicle/advisory" ||
      value.topic === "vyro/v1/preemption/request") &&
    typeof value.schema_version === "string" &&
    (value.vehicle_id === undefined || isNonEmptyString(value.vehicle_id)) &&
    (value.command_id === undefined || isNonEmptyString(value.command_id)) &&
    (value.ts_utc === undefined || isValidTimestamp(value.ts_utc)) &&
    (value.timestamp === undefined || isValidTimestamp(value.timestamp))
  );
}

export function parseTopicMessage(value: unknown): DashboardMessage | null {
  if (!isRecord(value) || !isWebSocketTopic(value.topic)) return null;

  switch (value.topic) {
    case "vyro/v1/vehicle/state":
      return isVehicleState(value) ? value : null;
    case "vyro/v1/intersection/state":
      return isIntersectionState(value) ? value : null;
    case "vyro/v1/controller/command":
      return isSignalCommand(value) ? value : null;
    case "vyro/v1/controller/ack":
      return isControllerAck(value) ? value : null;
    case "vyro/v1/metrics/snapshot":
      return isMetricsSnapshot(value) ? value : null;
    case "vyro/v1/vehicle/advisory":
    case "vyro/v1/preemption/request":
      return isAuxiliaryTopicMessage(value) ? value : null;
  }
}

export function messageTimestamp(
  message: DashboardMessage,
  receivedAt: number,
): number {
  const timestamp = message.ts_utc ?? message.timestamp;
  if (typeof timestamp !== "string") return receivedAt;
  const parsed = Date.parse(timestamp);
  return Number.isFinite(parsed) ? parsed : receivedAt;
}
