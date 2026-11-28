export const COMMAND_TIMEOUT_MS = 5_000;

export type CommandStatus = "pending" | "applied" | "rejected" | "timeout";

export interface CommandAcknowledgement {
  command_id: unknown;
  applied: unknown;
}

export function getCommandStatus(
  commandId: unknown,
  commandAgeMs: number,
  acknowledgements: readonly CommandAcknowledgement[],
  timeoutMs = COMMAND_TIMEOUT_MS,
): CommandStatus {
  const acknowledgement =
    typeof commandId === "string" && commandId.length > 0
      ? acknowledgements.find((item) => item.command_id === commandId)
      : undefined;

  if (typeof acknowledgement?.applied === "boolean") {
    return acknowledgement.applied ? "applied" : "rejected";
  }

  return commandAgeMs >= timeoutMs ? "timeout" : "pending";
}
