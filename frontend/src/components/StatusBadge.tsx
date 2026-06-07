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
