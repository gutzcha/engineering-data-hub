/*
 * ===
 * File Summary
 * Path: frontend\src\components\StatusBadge.tsx
 * Type: typescript
 * Purpose: Reusable UI component primitives used across feature screens.
 * Primary responsibilities:
 * - Domain behavior is summarized for fast onboarding and avoids full-file reread.
 * - Core symbols: StatusTone, StatusBadge
 * Inputs:
 * - Downstream and upstream interactions in the same domain.
 * Outputs:
 * - API payloads, records, side effects, or UI views depending on file role.
 * Dependencies:
 * - Shared runtime services and adjacent domain modules.
 * Known risks:
 * - Validate behavior after migrations, dependency upgrades, or contract changes.
 * ===
 * 
 */

import type { ReactNode } from "react";

export type StatusTone =
  | "active"
  | "ready"
  | "review"
  | "blocked"
  | "neutral"
  | "warning";

type StatusBadgeProps = {
  tone?: StatusTone;
  children: ReactNode;
};

export function StatusBadge({ tone = "neutral", children }: StatusBadgeProps) {
  return <span className={`status-badge status-${tone}`}>{children}</span>;
}

