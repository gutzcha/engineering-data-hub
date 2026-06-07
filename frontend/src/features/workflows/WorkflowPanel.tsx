import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, History, Loader2, Network } from "lucide-react";
import { useMemo, useState } from "react";

import { StatusBadge } from "../../components/StatusBadge";
import type { StatusTone } from "../../components/StatusBadge";
import { apiGet, apiPost } from "../../lib/api";
import type { WorkflowTask } from "./TaskInbox";

type WorkflowDefinition = {
  key?: string;
  label?: string;
  name?: string;
};

type WorkflowRecord = {
  id?: string | number;
  code?: string;
  title?: string;
  name?: string;
};

type WorkflowTransition = {
  key?: string;
  id?: string | number;
  label?: string;
  name?: string;
  to_state?: string;
  to?: string;
  guard_failures?: string[];
  errors?: string[] | Record<string, string[] | string>;
};

type WorkflowHistoryEvent = {
  id?: string | number;
  transition?: string;
  transition_key?: string;
  from_state?: string;
  to_state?: string;
  actor?: string;
  user?: string;
  created_at?: string;
  timestamp?: string;
};

export type WorkflowPanelData = {
  id?: string | number;
  definition?: WorkflowDefinition;
  record?: WorkflowRecord;
  state?: string;
  status?: string;
  tasks?: WorkflowTask[];
  open_tasks?: WorkflowTask[];
  available_transitions?: WorkflowTransition[];
  transitions?: WorkflowTransition[];
  guard_failures?: string[];
  errors?: string[] | Record<string, string[] | string>;
  transition_history?: WorkflowHistoryEvent[];
  history?: WorkflowHistoryEvent[];
};

type WorkflowPanelProps = {
  recordId?: string | number;
  workflow?: WorkflowPanelData;
  isLoading?: boolean;
  title?: string;
};

export function WorkflowPanel({
  recordId,
  workflow,
  isLoading = false,
  title = "Workflow"
}: WorkflowPanelProps) {
  const queryClient = useQueryClient();
  const [guardFailures, setGuardFailures] = useState<string[]>([]);

  const workflowQuery = useQuery({
    queryKey: ["records", recordId, "workflow"],
    queryFn: () => apiGet<WorkflowPanelData>(`/records/${recordId}/workflow/`),
    enabled: Boolean(recordId) && !workflow
  });

  const data = workflow ?? workflowQuery.data;
  const transitions = data?.available_transitions ?? data?.transitions ?? [];
  const openTasks = (data?.open_tasks ?? data?.tasks ?? []).filter(
    (task) => (task.state ?? task.status ?? "open") !== "complete"
  );
  const history = data?.transition_history ?? data?.history ?? [];
  const staticGuardFailures = useMemo(
    () => [
      ...(data?.guard_failures ?? []),
      ...flattenErrors(data?.errors),
      ...transitions.flatMap((transition) => [
        ...(transition.guard_failures ?? []),
        ...flattenErrors(transition.errors)
      ])
    ],
    [data?.guard_failures, transitions]
  );

  const transitionWorkflow = useMutation({
    mutationFn: (transitionKey: string | number) =>
      apiPost<WorkflowPanelData>(`/records/${recordId}/workflow/${transitionKey}/`, {}),
    onMutate: () => setGuardFailures([]),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["records", recordId, "workflow"] });
      void queryClient.invalidateQueries({ queryKey: ["records", recordId] });
    },
    onError: (error) => {
      setGuardFailures([errorMessage(error)]);
    }
  });

  const loading = isLoading || workflowQuery.isLoading;
  const failures = guardFailures.length ? guardFailures : staticGuardFailures;

  return (
    <section className="table-panel detail-panel workflow-panel" aria-labelledby="workflow-panel-title">
      <div className="panel-heading">
        <div>
          <p className="section-kicker">{data?.definition?.label ?? data?.definition?.name ?? "Workflow"}</p>
          <h2 id="workflow-panel-title">{title}</h2>
        </div>
        <StatusBadge tone={workflowTone(data?.state ?? data?.status)}>
          {loading ? "Loading" : humanize(data?.state ?? data?.status ?? "Not started")}
        </StatusBadge>
      </div>

      {(workflowQuery.error || transitionWorkflow.error) && (
        <div className="admin-alert project-inline-alert" role="alert">
          <strong>Workflow action failed</strong>
          <span>{errorMessage(workflowQuery.error ?? transitionWorkflow.error)}</span>
        </div>
      )}

      <div className="record-panel-body">
        <div className="workflow-state-grid" aria-label="Workflow status">
          <div className="admin-stat">
            <span>Current state</span>
            <strong>{humanize(data?.state ?? data?.status ?? "Not started")}</strong>
          </div>
          <div className="admin-stat">
            <span>Open tasks</span>
            <strong>{openTasks.length}</strong>
          </div>
          <div className="admin-stat">
            <span>Transitions</span>
            <strong>{transitions.length}</strong>
          </div>
        </div>

        <section className="workflow-subsection" aria-labelledby="workflow-transitions-title">
          <div className="project-section-heading">
            <h3 id="workflow-transitions-title">Available Transitions</h3>
          </div>
          <div className="record-action-row">
            {transitions.length === 0 ? (
              <p className="admin-muted">No workflow transitions are currently available.</p>
            ) : (
              transitions.map((transition) => (
                <button
                  className="button button-secondary"
                  type="button"
                  key={transition.key ?? transition.id ?? transition.label}
                  onClick={() => transitionWorkflow.mutate(transition.key ?? transition.id ?? "")}
                  disabled={!recordId || transitionWorkflow.isPending}
                >
                  {transitionWorkflow.isPending ? (
                    <Loader2 aria-hidden="true" size={16} />
                  ) : (
                    <Network aria-hidden="true" size={16} />
                  )}
                  {transition.label ?? transition.name ?? transition.to_state ?? transition.to ?? "Transition"}
                </button>
              ))
            )}
          </div>
        </section>

        <section className="workflow-subsection" aria-labelledby="workflow-guards-title">
          <div className="project-section-heading">
            <h3 id="workflow-guards-title">Guard Failures</h3>
          </div>
          {failures.length === 0 ? (
            <p className="admin-muted">No guard failures reported.</p>
          ) : (
            <div className="validation-list">
              {failures.map((failure, index) => (
                <div className="validation-item" key={`${failure}-${index}`}>
                  <span>
                    <AlertTriangle aria-hidden="true" size={14} /> {failure}
                  </span>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="workflow-subsection" aria-labelledby="workflow-open-tasks-title">
          <div className="project-section-heading">
            <h3 id="workflow-open-tasks-title">Open Tasks</h3>
          </div>
          <div className="event-list" role="list">
            {openTasks.length === 0 ? (
              <p className="admin-muted">No open workflow tasks.</p>
            ) : (
              openTasks.map((task) => (
                <div className="event-item" role="listitem" key={task.id}>
                  <div>
                    <strong>{task.title ?? task.name ?? `Task ${task.id}`}</strong>
                    <span>{task.assigned_role ?? task.role ?? "Unassigned"}</span>
                  </div>
                  <StatusBadge tone="review">{humanize(task.state ?? task.status ?? "open")}</StatusBadge>
                </div>
              ))
            )}
          </div>
        </section>

        <section className="workflow-subsection" aria-labelledby="workflow-history-title">
          <div className="project-section-heading">
            <h3 id="workflow-history-title">Transition History</h3>
          </div>
          <div className="event-list" role="list">
            {history.length === 0 ? (
              <p className="admin-muted">No workflow transitions recorded.</p>
            ) : (
              history.map((event, index) => (
                <div className="event-item" role="listitem" key={event.id ?? index}>
                  <div>
                    <strong>{event.transition ?? event.transition_key ?? "transition"}</strong>
                    <span>
                      {[event.from_state, event.to_state].filter(Boolean).join(" to ") || "State change"} ·{" "}
                      {event.actor ?? event.user ?? "System"} · {formatDateTime(event.created_at ?? event.timestamp)}
                    </span>
                  </div>
                  <History aria-hidden="true" size={16} />
                </div>
              ))
            )}
          </div>
        </section>
      </div>
    </section>
  );
}

function workflowTone(state?: string): StatusTone {
  if (state && ["released", "complete", "completed", "approved"].includes(state)) {
    return "ready";
  }

  if (state && ["blocked", "rejected", "failed"].includes(state)) {
    return "blocked";
  }

  if (state && ["review", "open", "pending"].includes(state)) {
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

function humanize(value: string) {
  return value.replace(/[_-]+/g, " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

function flattenErrors(errors?: string[] | Record<string, string[] | string>) {
  if (!errors) {
    return [];
  }

  if (Array.isArray(errors)) {
    return errors;
  }

  return Object.entries(errors).flatMap(([field, messages]) =>
    Array.isArray(messages)
      ? messages.map((message) => `${field}: ${message}`)
      : `${field}: ${messages}`
  );
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Workflow request failed.";
}
