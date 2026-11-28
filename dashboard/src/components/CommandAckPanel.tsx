import { useEffect, useState } from "react";
import {
  COMMAND_TIMEOUT_MS,
  getCommandStatus,
  type CommandAcknowledgement,
  type CommandStatus,
} from "../commandStatus";
import type { TrackedItem } from "../store";
import type { AckMessage, CommandMessage } from "../types";

type CommandHistoryItem = TrackedItem<CommandMessage | AckMessage>;

interface CommandAckPanelProps {
  history: CommandHistoryItem[];
  onMockMessage: (value: unknown) => void;
  useMockCommands: boolean;
  timeoutMs?: number;
}

interface CanonicalCommand {
  schema_version: string;
  command_id: string;
  signal_id: string;
  phase: string | number;
  hold_s: number;
  reason: string;
  ts_utc: string;
}

interface CanonicalAcknowledgement extends CommandAcknowledgement {
  schema_version: string;
  command_id: string;
  applied: boolean;
  reason: string;
}

interface CommandRow {
  command: CanonicalCommand;
  status: CommandStatus;
  reason: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function isPhase(value: unknown): value is string | number {
  return (
    isNonEmptyString(value) ||
    (typeof value === "number" && Number.isFinite(value))
  );
}

function isUtcTimestamp(value: unknown): value is string {
  return (
    typeof value === "string" &&
    value.endsWith("Z") &&
    Number.isFinite(Date.parse(value))
  );
}

function isCanonicalCommand(value: unknown): value is CanonicalCommand {
  return (
    isRecord(value) &&
    isNonEmptyString(value.schema_version) &&
    isNonEmptyString(value.command_id) &&
    isNonEmptyString(value.signal_id) &&
    isPhase(value.phase) &&
    typeof value.hold_s === "number" &&
    Number.isFinite(value.hold_s) &&
    value.hold_s > 0 &&
    isNonEmptyString(value.reason) &&
    isUtcTimestamp(value.ts_utc)
  );
}

function isCanonicalAcknowledgement(
  value: unknown,
): value is CanonicalAcknowledgement {
  return (
    isRecord(value) &&
    isNonEmptyString(value.schema_version) &&
    isNonEmptyString(value.command_id) &&
    isNonEmptyString(value.signal_id) &&
    isPhase(value.phase) &&
    typeof value.hold_s === "number" &&
    Number.isFinite(value.hold_s) &&
    value.hold_s > 0 &&
    typeof value.applied === "boolean" &&
    isNonEmptyString(value.reason) &&
    isUtcTimestamp(value.ts_utc)
  );
}

function formatLocalTime(timestamp: string): string {
  const date = new Date(timestamp);
  if (!Number.isFinite(date.getTime())) return "—";
  return [date.getHours(), date.getMinutes(), date.getSeconds()]
    .map((value) => String(value).padStart(2, "0"))
    .join(":");
}

export function CommandAckPanel({
  history,
  onMockMessage,
  useMockCommands,
  timeoutMs = COMMAND_TIMEOUT_MS,
}: CommandAckPanelProps) {
  const [signalFilter, setSignalFilter] = useState("");
  const [onlyRejectedOrTimeout, setOnlyRejectedOrTimeout] = useState(false);
  const [now, setNow] = useState(Date.now);

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 250);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!useMockCommands) return;

    let sequence = 0;
    const acknowledgementTimers = new Set<number>();
    const commandTimer = window.setInterval(() => {
      sequence += 1;
      const commandId = `mock-command-${Date.now()}-${sequence}`;
      const signalId = `signal-${Math.floor(Math.random() * 5) + 1}`;
      const commandTime = new Date().toISOString();
      const command = {
        topic: "vyro/v1/controller/command",
        schema_version: "0.2",
        command_id: commandId,
        signal_id: signalId,
        phase: Math.floor(Math.random() * 4) + 1,
        hold_s: 10,
        reason: "mock_generated",
        ts_utc: commandTime,
      };
      onMockMessage(command);

      if (Math.random() < 0.15) return;

      const rejected = Math.random() < 0.25;
      const acknowledgementTimer = window.setTimeout(() => {
        acknowledgementTimers.delete(acknowledgementTimer);
        onMockMessage({
          topic: "vyro/v1/controller/ack",
          schema_version: command.schema_version,
          command_id: command.command_id,
          signal_id: command.signal_id,
          phase: command.phase,
          hold_s: command.hold_s,
          applied: !rejected,
          reason: rejected ? "mock_rejected" : "mock_applied",
          ts_utc: new Date().toISOString(),
        });
      }, 300);
      acknowledgementTimers.add(acknowledgementTimer);
    }, 2_000);

    return () => {
      window.clearInterval(commandTimer);
      acknowledgementTimers.forEach((timer) => window.clearTimeout(timer));
      acknowledgementTimers.clear();
    };
  }, [onMockMessage, useMockCommands]);

  const commands = history.flatMap((item) => {
    if (
      item.value.topic !== "vyro/v1/controller/command" ||
      !isCanonicalCommand(item.value)
    ) {
      return [];
    }
    return [{ item, command: item.value }];
  });
  const acknowledgements = history.flatMap((item) => {
    if (
      item.value.topic !== "vyro/v1/controller/ack" ||
      !isCanonicalAcknowledgement(item.value)
    ) {
      return [];
    }
    return [item.value];
  });
  const signals = [...new Set(commands.map(({ command }) => command.signal_id))]
    .sort((left, right) => left.localeCompare(right));
  const rows: CommandRow[] = commands
    .map(({ item, command }) => {
      const acknowledgement = acknowledgements.find(
        (candidate) => candidate.command_id === command.command_id,
      );
      const ageMs = Math.max(0, now - Date.parse(command.ts_utc));
      const status = getCommandStatus(
        command.command_id,
        ageMs,
        acknowledgements,
        timeoutMs,
      );
      return {
        command,
        status,
        reason:
          status === "timeout"
            ? "Acknowledgement timed out"
            : acknowledgement?.reason ?? command.reason,
      };
    })
    .filter(
      ({ command, status }) =>
        (!signalFilter || command.signal_id === signalFilter) &&
        (!onlyRejectedOrTimeout ||
          status === "rejected" ||
          status === "timeout"),
    )
    .sort(
      (left, right) =>
        Date.parse(right.command.ts_utc) - Date.parse(left.command.ts_utc),
    );

  return (
    <section className="card command-ack-panel" aria-labelledby="command-ack-heading">
      <div className="command-ack-header">
        <div className="panel-heading">
          <h2 id="command-ack-heading">Command / acknowledgement log</h2>
          <p>Signal phase requests and bridge outcomes.</p>
        </div>
        <div className="command-ack-filters">
          <label>
            <span>Signal</span>
            <select
              aria-label="Filter by signal"
              value={signalFilter}
              onChange={(event) => setSignalFilter(event.target.value)}
            >
              <option value="">All signals</option>
              {signals.map((signal) => (
                <option key={signal} value={signal}>
                  {signal}
                </option>
              ))}
            </select>
          </label>
          <label className="rejected-filter">
            <input
              type="checkbox"
              checked={onlyRejectedOrTimeout}
              onChange={(event) =>
                setOnlyRejectedOrTimeout(event.target.checked)
              }
            />
            <span>Only rejected/timeout</span>
          </label>
        </div>
      </div>
      {rows.length === 0 ? (
        <p className="command-ack-empty">
          {commands.length === 0
            ? "No commands yet"
            : "No commands match the selected filters."}
        </p>
      ) : (
        <div className="command-ack-table-wrap">
          <table className="command-ack-table">
            <thead>
              <tr>
                <th scope="col">Time</th>
                <th scope="col">Signal</th>
                <th scope="col">Target phase</th>
                <th scope="col">Hold (s)</th>
                <th scope="col">Status</th>
                <th scope="col">Reason</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(({ command, status, reason }) => (
                <tr key={command.command_id}>
                  <td>{formatLocalTime(command.ts_utc)}</td>
                  <td>{command.signal_id}</td>
                  <td>{command.phase}</td>
                  <td>{command.hold_s}</td>
                  <td>
                    <span className={`command-status command-status-${status}`}>
                      {status}
                    </span>
                  </td>
                  <td>{reason || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
