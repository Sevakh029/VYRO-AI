export type WebSocketTopic =
  | "vyro/v1/vehicle/state"
  | "vyro/v1/intersection/state"
  | "vyro/v1/controller/command"
  | "vyro/v1/controller/ack"
  | "vyro/v1/vehicle/advisory"
  | "vyro/v1/metrics/snapshot"
  | "vyro/v1/preemption/request";

export interface VehicleState {
  schema_version: "0.2";
  vehicle_id: string;
  latitude: number;
  longitude: number;
  speed_mps: number;
  heading_deg: number;
  timestamp: string;
  vehicle_type: "car" | "minibus" | "truck" | "emergency" | "unknown";
}

export interface TopicMessage {
  topic: WebSocketTopic;
  vehicle_id?: string;
  intersection_id?: string;
  command_id?: string;
  timestamp?: string;
  [key: string]: unknown;
}

export type TopicMessageStore = Partial<
  Record<WebSocketTopic, Record<string, TopicMessage>>
>;

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

export function isWebSocketTopic(value: unknown): value is WebSocketTopic {
  return (
    typeof value === "string" &&
    WEB_SOCKET_TOPICS.some((topic) => topic === value)
  );
}

export function parseTopicMessage(value: unknown): TopicMessage | null {
  if (
    typeof value !== "object" ||
    value === null ||
    !("topic" in value) ||
    !isWebSocketTopic(value.topic)
  ) {
    return null;
  }
  return { ...value, topic: value.topic };
}

export function messageKey(message: TopicMessage): string {
  return (
    message.vehicle_id ??
    message.intersection_id ??
    message.command_id ??
    message.timestamp ??
    "latest"
  );
}

export function pruneStaleVehicleStates(
  messages: TopicMessageStore,
  now = Date.now(),
): TopicMessageStore {
  const vehicles = messages["vyro/v1/vehicle/state"];
  if (!vehicles) return messages;

  const currentVehicles = Object.entries(vehicles);
  const freshVehicles = currentVehicles.filter(([, message]) => {
    if (typeof message.timestamp !== "string") return false;
    const timestamp = Date.parse(message.timestamp);
    return (
      Number.isFinite(timestamp) &&
      Math.abs(now - timestamp) <= VEHICLE_STATE_TTL_MS
    );
  });
  if (freshVehicles.length === currentVehicles.length) return messages;

  return {
    ...messages,
    "vyro/v1/vehicle/state": Object.fromEntries(freshVehicles),
  };
}
