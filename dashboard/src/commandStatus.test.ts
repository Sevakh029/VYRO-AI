import { describe, expect, it } from "vitest";
import { getCommandStatus } from "./commandStatus";

describe("getCommandStatus", () => {
  it("reports pending when there is no acknowledgement before the timeout", () => {
    expect(getCommandStatus("command-1", 4_999, [])).toBe("pending");
  });

  it("matches an applied acknowledgement by command_id", () => {
    expect(
      getCommandStatus("command-1", 100, [
        { command_id: "other-command", applied: false },
        { command_id: "command-1", applied: true },
      ]),
    ).toBe("applied");
  });

  it("reports a rejection for an acknowledgement with applied=false", () => {
    expect(
      getCommandStatus("command-1", 100, [
        { command_id: "command-1", applied: false },
      ]),
    ).toBe("rejected");
  });

  it("reports timeout when no matching acknowledgement arrives after five seconds", () => {
    expect(
      getCommandStatus("command-1", 5_000, [
        { command_id: "other-command", applied: true },
      ]),
    ).toBe("timeout");
  });
});
