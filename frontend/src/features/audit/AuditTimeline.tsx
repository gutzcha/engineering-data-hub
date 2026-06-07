import { useQuery } from "@tanstack/react-query";
import { History, Link as LinkIcon, Loader2 } from "lucide-react";
import { Link } from "react-router-dom";

import { StatusBadge } from "../../components/StatusBadge";
import { apiGet } from "../../lib/api";

type AuditEvent = {
  id: string | number;
  actor?: string | number | null;
  actor_username?: string | null;
  action: string;
  object_type: string;
  object_id: string;
  before?: Record<string, unknown> | null;
  after?: Record<string, unknown> | null;
  request_id?: string;
  ip_address?: string | null;
  user_agent?: string;
  created_at: string;
};

type AuditResponse = {
  results?: AuditEvent[];
};

type AuditTimelineProps = {
  endpoint?: string;
  title?: string;
};

export function AuditTimeline({ endpoint = "/audit/?limit=100", title = "Audit Timeline" }: AuditTimelineProps) {
  const auditQuery = useQuery({
    queryKey: ["audit", endpoint],
    queryFn: () => apiGet<AuditResponse>(endpoint)
  });

  const events = auditQuery.data?.results ?? [];

  return (
    <div className="page-stack audit-page">
      <section className="workspace-header" aria-labelledby="audit-timeline-title">
        <div>
          <p className="section-kicker">Append-only system history</p>
          <h1 id="audit-timeline-title">{title}</h1>
        </div>
        <StatusBadge tone={events.length ? "active" : "neutral"}>
          {auditQuery.isLoading ? "Loading" : `${events.length} Events`}
        </StatusBadge>
      </section>

      {auditQuery.error && (
        <div className="admin-alert" role="alert">
          <strong>Audit timeline failed</strong>
          <span>{errorMessage(auditQuery.error)}</span>
        </div>
      )}

      <section className="table-panel" aria-labelledby="audit-list-title">
        <div className="panel-heading">
          <div>
            <p className="section-kicker">Timeline</p>
            <h2 id="audit-list-title">Events</h2>
          </div>
          {auditQuery.isLoading ? (
            <Loader2 aria-hidden="true" size={18} />
          ) : (
            <History aria-hidden="true" size={18} />
          )}
        </div>
        <div className="audit-timeline" role="list" aria-label="Audit events">
          {events.length === 0 ? (
            <p className="admin-muted">
              {auditQuery.isLoading ? "Loading audit events." : "No audit events found."}
            </p>
          ) : (
            events.map((event) => <AuditTimelineItem event={event} key={event.id} />)
          )}
        </div>
      </section>
    </div>
  );
}

function AuditTimelineItem({ event }: { event: AuditEvent }) {
  return (
    <article className="audit-item" role="listitem">
      <div className="audit-item-main">
        <strong>{event.action}</strong>
        <span>
          {event.actor_username ?? event.actor ?? "System"} · {formatDateTime(event.created_at)}
        </span>
      </div>
      <div className="audit-object-link">
        <LinkIcon aria-hidden="true" size={15} />
        {objectHref(event) ? (
          <Link className="text-link" to={objectHref(event) ?? "#"}>
            {event.object_type}:{event.object_id}
          </Link>
        ) : (
          <span>
            {event.object_type}:{event.object_id}
          </span>
        )}
      </div>
      <div className="audit-change-list" aria-label={`Old and new values for ${event.action}`}>
        <AuditValue label="Old" value={event.before} />
        <AuditValue label="New" value={event.after} />
      </div>
    </article>
  );
}

function AuditValue({ label, value }: { label: string; value?: Record<string, unknown> | null }) {
  return (
    <div>
      <span>{label}</span>
      <code>{summarizeValue(value)}</code>
    </div>
  );
}

function summarizeValue(value?: Record<string, unknown> | null) {
  if (!value || Object.keys(value).length === 0) {
    return "None";
  }
  return Object.entries(value)
    .slice(0, 6)
    .map(([key, item]) => `${key}: ${formatValue(item)}`)
    .join("; ");
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "none";
  }
  if (Array.isArray(value)) {
    return `[${value.map(formatValue).join(", ")}]`;
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}

function objectHref(event: AuditEvent) {
  if (event.object_type === "record") {
    return `/records/${event.object_id}`;
  }
  if (event.object_type === "document") {
    return `/documents/${event.object_id}`;
  }
  if (event.object_type === "folderchangeevent") {
    return `/tasks/folder-events/${event.object_id}`;
  }
  return undefined;
}

function formatDateTime(value?: string) {
  if (!value) {
    return "Not recorded";
  }
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Audit request failed.";
}
