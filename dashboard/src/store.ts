import {
  messageTimestamp,
  parseTopicMessage,
  STALE_THRESHOLD_MS,
  VEHICLE_STATE_TTL_MS,
  type AckMessage,
  type AuxiliaryTopicMessage,
  type CommandMessage,
  type DashboardMessage,
  type IntersectionState,
  type MetricsSnapshot,
  type VehicleState,
  type WebSocketStatus,
} from "./types";

export interface TrackedItem<T> {
  value: T;
  lastUpdated: number;
  stale: boolean;
  source: "live" | "mock";
}

export interface DashboardStore {
  vehicles: Record<string, TrackedItem<VehicleState>>;
  intersections: Record<string, TrackedItem<IntersectionState>>;
  commandHistory: TrackedItem<CommandMessage | AckMessage>[];
  metrics: TrackedItem<MetricsSnapshot> | null;
  advisories: Record<string, TrackedItem<AuxiliaryTopicMessage>>;
  hasLiveIntersectionData: boolean;
  hasLiveCommandData: boolean;
  hasLiveMetricsData: boolean;
  status: WebSocketStatus;
  droppedMessages: number;
}

export type DashboardStoreAction =
  | { type: "status"; status: WebSocketStatus }
  | { type: "reconnecting" }
  | {
      type: "message";
      value: unknown;
      receivedAt: number;
      source?: "live" | "mock";
    }
  | { type: "prune"; now: number }
  | { type: "dropped-message" };

export function createInitialDashboardStore(): DashboardStore {
  return {
    vehicles: {},
    intersections: {},
    commandHistory: [],
    metrics: null,
    advisories: {},
    hasLiveIntersectionData: false,
    hasLiveCommandData: false,
    hasLiveMetricsData: false,
    status: "connecting",
    droppedMessages: 0,
  };
}

export function isStale<T>(
  item: TrackedItem<T> | null | undefined,
  now: number,
  thresholdMs = STALE_THRESHOLD_MS,
): boolean {
  return (
    item !== null &&
    item !== undefined &&
    (item.stale || now - item.lastUpdated > thresholdMs)
  );
}

function markStale<T>(
  items: Record<string, TrackedItem<T>>,
): Record<string, TrackedItem<T>> {
  return Object.fromEntries(
    Object.entries(items).map(([key, item]) => [
      key,
      { ...item, stale: true },
    ]),
  );
}

function markStoreStale(store: DashboardStore): DashboardStore {
  return {
    ...store,
    vehicles: markStale(store.vehicles),
    intersections: markStale(store.intersections),
    commandHistory: store.commandHistory.map((item) => ({
      ...item,
      stale: true,
    })),
    metrics: store.metrics ? { ...store.metrics, stale: true } : null,
    advisories: markStale(store.advisories),
    status: "reconnecting",
  };
}

function tracked<T>(
  value: T,
  lastUpdated: number,
  source: "live" | "mock",
): TrackedItem<T> {
  return { value, lastUpdated, stale: false, source };
}

function getSignalId(message: IntersectionState): string {
  return message.signal_id ?? message.intersection_id ?? "";
}

function getCommandId(message: CommandMessage | AckMessage): string {
  return message.command_id;
}

function upsertCommand(
  history: TrackedItem<CommandMessage | AckMessage>[],
  incoming: TrackedItem<CommandMessage | AckMessage>,
): TrackedItem<CommandMessage | AckMessage>[] {
  const message = incoming.value;
  const index = history.findIndex(
    (entry) =>
      entry.value.topic === message.topic &&
      getCommandId(entry.value) === getCommandId(message),
  );

  if (index >= 0) {
    const updated = [...history];
    updated[index] = incoming;
    return updated;
  }

  return [...history, incoming].slice(-100);
}

function updateMessage(
  store: DashboardStore,
  message: DashboardMessage,
  receivedAt: number,
  source: "live" | "mock",
): DashboardStore {
  const lastUpdated = messageTimestamp(message, receivedAt);

  switch (message.topic) {
    case "vyro/v1/vehicle/state":
      return {
        ...store,
        vehicles: {
          ...store.vehicles,
          [message.vehicle_id]: tracked(message, lastUpdated, source),
        },
      };
    case "vyro/v1/intersection/state":
      const currentIntersections =
        source === "live"
          ? Object.fromEntries(
              Object.entries(store.intersections).filter(
                ([, item]) => item.source !== "mock",
              ),
            )
          : store.intersections;
      return {
        ...store,
        hasLiveIntersectionData:
          store.hasLiveIntersectionData || source === "live",
        intersections: {
          ...currentIntersections,
          [getSignalId(message)]: tracked(message, lastUpdated, source),
        },
      };
    case "vyro/v1/controller/command":
    case "vyro/v1/controller/ack": {
      const commandHistory =
        source === "live"
          ? store.commandHistory.filter((item) => item.source !== "mock")
          : store.commandHistory;
      return {
        ...store,
        hasLiveCommandData: store.hasLiveCommandData || source === "live",
        commandHistory: upsertCommand(
          commandHistory,
          tracked(message, lastUpdated, source),
        ),
      };
    }
    case "vyro/v1/metrics/snapshot":
      return {
        ...store,
        metrics: tracked(message, lastUpdated, source),
        hasLiveMetricsData: store.hasLiveMetricsData || source === "live",
      };
    case "vyro/v1/vehicle/advisory": {
      const key =
        message.vehicle_id ??
        message.command_id ??
        message.ts_utc ??
        message.timestamp ??
        String(receivedAt);
      return {
        ...store,
        advisories: {
          ...store.advisories,
          [key]: tracked(message, lastUpdated, source),
        },
      };
    }
    case "vyro/v1/preemption/request":
      return store;
  }
}

export function pruneExpiredVehicles(
  store: DashboardStore,
  now = Date.now(),
): DashboardStore {
  const vehicles = Object.fromEntries(
    Object.entries(store.vehicles).filter(
      ([, item]) => now - item.lastUpdated <= VEHICLE_STATE_TTL_MS,
    ),
  );
  return Object.keys(vehicles).length === Object.keys(store.vehicles).length
    ? store
    : { ...store, vehicles };
}

export function dashboardStoreReducer(
  store: DashboardStore,
  action: DashboardStoreAction,
): DashboardStore {
  switch (action.type) {
    case "status":
      return { ...store, status: action.status };
    case "reconnecting":
      return markStoreStale(store);
    case "prune":
      return pruneExpiredVehicles(store, action.now);
    case "dropped-message":
      return { ...store, droppedMessages: store.droppedMessages + 1 };
    case "message": {
      const message = parseTopicMessage(action.value);
      const source = action.source ?? "live";
      if (!message) {
        return { ...store, droppedMessages: store.droppedMessages + 1 };
      }
      if (source === "mock") {
        if (
          (message.topic === "vyro/v1/intersection/state" &&
            store.hasLiveIntersectionData) ||
          ((message.topic === "vyro/v1/controller/command" ||
            message.topic === "vyro/v1/controller/ack") &&
            store.hasLiveCommandData) ||
          (message.topic === "vyro/v1/metrics/snapshot" &&
            store.hasLiveMetricsData) ||
          (message.topic !== "vyro/v1/intersection/state" &&
            message.topic !== "vyro/v1/controller/command" &&
            message.topic !== "vyro/v1/controller/ack" &&
            message.topic !== "vyro/v1/metrics/snapshot")
        ) {
          return store;
        }
      }
      return updateMessage(store, message, action.receivedAt, source);
    }
  }
}
