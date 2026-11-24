export type WebSocketTopic =
  | "vyro/v1/vehicle/state"
  | "vyro/v1/intersection/state"
  | "vyro/v1/controller/command"
  | "vyro/v1/controller/ack"
  | "vyro/v1/vehicle/advisory"
  | "vyro/v1/metrics/snapshot";

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
