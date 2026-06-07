import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CheckCircle2,
  FilePlus2,
  FolderSearch,
  Loader2,
  UserPlus,
  XCircle
} from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { DataTable } from "../../components/DataTable";
import { StatusBadge } from "../../components/StatusBadge";
import { apiGet, apiPost } from "../../lib/api";

type FolderChangeEvent = {
  id: string | number;
  event_type: string;
  path: string;
  detected_hash?: string;
  matched_record?: string | number | null;
  managed_folder?: string | number | null;
  review_status: string;
  reviewer?: string | number | null;
  reviewer_username?: string | null;
  assigned_to?: string | number | null;
  assignee?: string | number | null;
  assignee_username?: string | null;
  created_at?: string;
  updated_at?: string;
};

type LinkDocumentResponse = {
  event: FolderChangeEvent;
  document?: {
    id: string | number;
    title?: string;
  };
};

type FolderEventResponse = FolderChangeEvent[] | { results?: FolderChangeEvent[] };

export function FolderReviewInbox() {
  const { eventId } = useParams();
  const queryClient = useQueryClient();
  const [assigneeByEvent, setAssigneeByEvent] = useState<Record<string, string>>({});
  const [notice, setNotice] = useState("");

  const eventsQuery = useQuery({
    queryKey: ["folder-events", "pending"],
    queryFn: () => apiGet<FolderEventResponse>("/folder-events/?review_status=pending")
  });

  const eventDetailQuery = useQuery({
    queryKey: ["folder-events", "detail", eventId],
    queryFn: () => apiGet<FolderChangeEvent>(`/folder-events/${eventId}/`),
    enabled: Boolean(eventId)
  });

  const acceptEvent = useMutation({
    mutationFn: (id: string | number) => apiPost<FolderChangeEvent>(`/folder-events/${id}/accept/`, {}),
    onSuccess: () => invalidateEvents(queryClient)
  });

  const ignoreEvent = useMutation({
    mutationFn: (id: string | number) => apiPost<FolderChangeEvent>(`/folder-events/${id}/ignore/`, {}),
    onSuccess: () => invalidateEvents(queryClient)
  });

  const linkDocument = useMutation({
    mutationFn: (id: string | number) =>
      apiPost<LinkDocumentResponse>(`/folder-events/${id}/link-document/`, {}),
    onSuccess: (response) => {
      setNotice(
        response.document
          ? `Linked document ${response.document.title ?? response.document.id}`
          : "Folder event linked."
      );
      invalidateEvents(queryClient);
    }
  });

  const assignEvent = useMutation({
    mutationFn: ({ id, assignedTo }: { id: string | number; assignedTo: string }) =>
      apiPost<FolderChangeEvent>(`/folder-events/${id}/assign/`, { assigned_to: assignedTo }),
    onSuccess: () => invalidateEvents(queryClient)
  });

  const events = itemsFromResponse(eventsQuery.data);
  const selectedEvent = eventId
    ? eventDetailQuery.data ?? events.find((event) => String(event.id) === eventId)
    : undefined;
  const error =
    eventsQuery.error ??
    eventDetailQuery.error ??
    acceptEvent.error ??
    ignoreEvent.error ??
    linkDocument.error ??
    assignEvent.error;

  return (
    <div className="page-stack folder-review-page">
      <section className="workspace-header" aria-labelledby="folder-review-title">
        <div>
          <p className="section-kicker">Managed folder changes</p>
          <h1 id="folder-review-title">
            {eventId ? `Folder Event ${eventId}` : "Folder Review Inbox"}
          </h1>
        </div>
        <StatusBadge tone={events.length ? "review" : "ready"}>
          {eventsQuery.isLoading ? "Loading" : `${events.length} Pending`}
        </StatusBadge>
      </section>

      {notice && (
        <div className="validation-success" role="status">
          <CheckCircle2 aria-hidden="true" size={18} />
          {notice}
        </div>
      )}

      {error && (
        <div className="admin-alert" role="alert">
          <strong>Folder review action failed</strong>
          <span>{errorMessage(error)}</span>
        </div>
      )}

      {selectedEvent && (
        <section className="filter-panel" aria-label="Selected folder event">
          <div className="active-filter-row">
            <StatusBadge tone="active">Selected event {selectedEvent.id}</StatusBadge>
            <span>{selectedEvent.path}</span>
          </div>
        </section>
      )}

      <section className="table-panel" aria-labelledby="folder-review-table-title">
        <div className="panel-heading">
          <div>
            <p className="section-kicker">Pending events</p>
            <h2 id="folder-review-table-title">Folder Events</h2>
          </div>
          <FolderSearch aria-hidden="true" size={18} />
        </div>
        <DataTable
          data={events}
          emptyMessage={eventsQuery.isLoading ? "Loading folder events." : "No folder events need review."}
          columns={[
            {
              id: "event",
              header: "Event",
              cell: ({ row }) => (
                <div className="task-title-cell">
                  <strong>{humanize(row.original.event_type)}</strong>
                  <span>{row.original.path}</span>
                </div>
              )
            },
            {
              id: "record",
              header: "Record",
              cell: ({ row }) =>
                row.original.matched_record ? (
                  <Link className="text-link" to={`/records/${row.original.matched_record}`}>
                    {row.original.matched_record}
                  </Link>
                ) : (
                  "Unmatched"
                )
            },
            {
              id: "assignment",
              header: "Assignment",
              cell: ({ row }) => (
                <div className="task-title-cell">
                  <strong>{row.original.assignee_username ?? "Unassigned"}</strong>
                  <span>{formatDateTime(row.original.created_at)}</span>
                </div>
              )
            },
            {
              id: "actions",
              header: "Actions",
              cell: ({ row }) => {
                const event = row.original;
                const assignmentValue = assigneeByEvent[String(event.id)] ?? "";

                return (
                  <div className="folder-event-actions">
                    <button
                      className="button button-secondary"
                      type="button"
                      onClick={() => acceptEvent.mutate(event.id)}
                      disabled={acceptEvent.isPending}
                    >
                      <CheckCircle2 aria-hidden="true" size={16} />
                      Accept
                    </button>
                    <button
                      className="button button-secondary"
                      type="button"
                      onClick={() => ignoreEvent.mutate(event.id)}
                      disabled={ignoreEvent.isPending}
                    >
                      <XCircle aria-hidden="true" size={16} />
                      Ignore
                    </button>
                    <button
                      className="button button-secondary"
                      type="button"
                      onClick={() => linkDocument.mutate(event.id)}
                      disabled={linkDocument.isPending || (!event.matched_record && !event.managed_folder)}
                    >
                      <FilePlus2 aria-hidden="true" size={16} />
                      Link Document
                    </button>
                    <label className="field-control folder-event-assignee">
                      <span>Assign</span>
                      <input
                        aria-label={`Assign user for event ${event.id}`}
                        value={assignmentValue}
                        onChange={(inputEvent) =>
                          setAssigneeByEvent((current) => ({
                            ...current,
                            [String(event.id)]: inputEvent.target.value
                          }))
                        }
                        placeholder="User ID"
                      />
                    </label>
                    <button
                      className="button button-secondary"
                      type="button"
                      onClick={() => assignEvent.mutate({ id: event.id, assignedTo: assignmentValue })}
                      disabled={assignEvent.isPending}
                    >
                      {assignEvent.isPending ? (
                        <Loader2 aria-hidden="true" size={16} />
                      ) : (
                        <UserPlus aria-hidden="true" size={16} />
                      )}
                      Assign
                    </button>
                  </div>
                );
              }
            }
          ]}
        />
      </section>
    </div>
  );
}

function invalidateEvents(queryClient: ReturnType<typeof useQueryClient>) {
  void queryClient.invalidateQueries({ queryKey: ["folder-events"] });
}

function itemsFromResponse(response?: FolderEventResponse) {
  if (Array.isArray(response)) {
    return response;
  }
  return response?.results ?? [];
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

function humanize(value: string) {
  return value.replace(/[_-]+/g, " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Folder review request failed.";
}
