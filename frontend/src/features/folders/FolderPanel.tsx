import { CheckCircle2, FolderSync, RotateCw } from "lucide-react";

import { StatusBadge } from "../../components/StatusBadge";

export type FolderInfo = {
  path?: string;
  generated_path?: string;
  state?: string;
  status?: string;
  recent_changes?: FolderEvent[];
};

export type FolderEvent = {
  id: string | number;
  title?: string;
  summary?: string;
  path?: string;
  status?: string;
  detected_at?: string;
  created_at?: string;
};

type FolderPanelProps = {
  folder?: FolderInfo;
  events?: FolderEvent[];
  isGenerating?: boolean;
  onGenerate?: () => void;
  onAcceptEvent?: (eventId: string | number) => void;
  onIgnoreEvent?: (eventId: string | number) => void;
};

export function FolderPanel({
  folder,
  events = [],
  isGenerating = false,
  onGenerate,
  onAcceptEvent,
  onIgnoreEvent
}: FolderPanelProps) {
  const path = folder?.path ?? folder?.generated_path ?? "No managed folder generated";
  const folderEvents = events.length > 0 ? events : folder?.recent_changes ?? [];
  const state = folder?.state ?? folder?.status ?? "not generated";

  return (
    <section className="table-panel detail-panel" aria-labelledby="folder-panel-title">
      <div className="panel-heading">
        <div>
          <p className="section-kicker">Managed folder</p>
          <h2 id="folder-panel-title">Folder</h2>
        </div>
        <StatusBadge tone={stateTone(state)}>{state}</StatusBadge>
      </div>
      <div className="record-panel-body">
        <div className="path-preview">
          <span>Generated path</span>
          <strong>{path}</strong>
        </div>
        <div className="record-action-row">
          <button
            className="button button-secondary"
            type="button"
            onClick={onGenerate}
            disabled={!onGenerate || isGenerating}
          >
            {isGenerating ? (
              <RotateCw aria-hidden="true" size={16} />
            ) : (
              <FolderSync aria-hidden="true" size={16} />
            )}
            Generate Folder
          </button>
        </div>
        <div className="event-list" role="list" aria-label="Recent folder changes">
          {folderEvents.length === 0 ? (
            <p className="admin-muted">No detected folder changes are waiting for review.</p>
          ) : (
            folderEvents.map((event) => (
              <div className="event-item" role="listitem" key={event.id}>
                <div>
                  <strong>{event.title ?? event.summary ?? `Folder event ${event.id}`}</strong>
                  <span>{event.path ?? formatDateTime(event.detected_at ?? event.created_at)}</span>
                </div>
                <div className="record-action-row">
                  <button
                    className="button button-secondary"
                    type="button"
                    onClick={() => onAcceptEvent?.(event.id)}
                    disabled={!onAcceptEvent}
                  >
                    <CheckCircle2 aria-hidden="true" size={16} />
                    Accept Change
                  </button>
                  <button
                    className="button button-secondary"
                    type="button"
                    onClick={() => onIgnoreEvent?.(event.id)}
                    disabled={!onIgnoreEvent}
                  >
                    <CheckCircle2 aria-hidden="true" size={16} />
                    Ignore Change
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </section>
  );
}

function stateTone(state: string) {
  const normalized = state.toLowerCase();

  if (normalized.includes("sync") || normalized.includes("ready")) {
    return "ready";
  }

  if (normalized.includes("review") || normalized.includes("change")) {
    return "review";
  }

  return "neutral";
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
