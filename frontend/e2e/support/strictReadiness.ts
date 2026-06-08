import { test } from "@playwright/test";

export function readinessGate(condition: boolean, message: string) {
  if (!condition) {
    return;
  }

  if (process.env.STRICT_CLIENT_READINESS === "true") {
    throw new Error(message);
  }

  test.skip(true, message);
}
