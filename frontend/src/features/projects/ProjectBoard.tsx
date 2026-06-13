/*
 * ===
 * File Summary
 * Path: frontend\src\features\projects\ProjectBoard.tsx
 * Type: typescript
 * Purpose: Frontend feature module implementing business flows and UI surfaces.
 * Primary responsibilities:
 * - Domain behavior is summarized for fast onboarding and avoids full-file reread.
 * - Core symbols: ProjectTask, ProjectColumn, ProjectSummary, ProjectBoardPayload, ProjectBoard
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

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Loader2 } from "lucide-react";

import { StatusBadge } from "../../components/StatusBadge";
import type { StatusTone } from "../../components/StatusBadge";
import { apiGet, apiPatch } from "../../lib/api";

export type ProjectTask = {
  id: string | number;
  title?: string;
  name?: string;
  state?: string;
  column?: string;
  owner?: string;
  assignee?: string;
  assigned_to?: string;
  due_at?: string;
  due_date?: string;
  start_date?: string;
  end_date?: string;
  sort_order?: number;
};

export type ProjectColumn = {
  key?: string;
  id?: string | number;
  title?: string;
  label?: string;
  name?: string;
  tasks?: ProjectTask[];
};

type NormalizedColumn = {
  columnId: number | null;
  key: string;
  label: string;
  selectValue: string;
  tasks: ProjectTask[];
};

export type ProjectSummary = {
  id?: string | number;
  record?: string | number;
  record_code?: string;
  code?: string;
  title?: string;
  name?: string;
  status?: string;
};

export type ProjectBoardPayload = {
  project?: ProjectSummary;
  columns?: ProjectColumn[];
  unassigned_tasks?: ProjectTask[];
};

type ProjectBoardProps = {
  projectId: string | number;
};

export function ProjectBoard({ projectId }: ProjectBoardProps) {
  const queryClient = useQueryClient();
  const boardQuery = useQuery({
    queryKey: ["projects", projectId, "board"],
    queryFn: () => apiGet<ProjectBoardPayload>(`/projects/${projectId}/board/`),
    enabled: Boolean(projectId)
  });

  const columns = normalizeColumns(boardQuery.data);

  const moveTask = useMutation({
    mutationFn: ({ taskId, column, sortOrder }: { taskId: string | number; column: number | null; sortOrder: number }) =>
      apiPatch<ProjectTask>(`/project-tasks/${taskId}/move/`, {
        column,
        sort_order: sortOrder
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["projects", projectId, "board"] });
      void queryClient.invalidateQueries({ queryKey: ["projects", projectId, "timeline"] });
      void queryClient.invalidateQueries({ queryKey: ["projects", "workload"] });
    }
  });

  return (
    <section className="table-panel project-board-panel" aria-labelledby="project-board-title">
      <div className="panel-heading">
        <div>
          <p className="section-kicker">Board</p>
          <h2 id="project-board-title">Project Board</h2>
        </div>
        <StatusBadge tone={columns.some((column) => column.tasks.length) ? "active" : "neutral"}>
          {boardQuery.isLoading ? "Loading" : `${columns.reduce((total, column) => total + column.tasks.length, 0)} Tasks`}
        </StatusBadge>
      </div>

      {(boardQuery.error || moveTask.error) && (
        <div className="admin-alert project-inline-alert" role="alert">
          <strong>{moveTask.error ? "Task move failed" : "Board failed"}</strong>
          <span>{errorMessage(moveTask.error ?? boardQuery.error)}</span>
        </div>
      )}

      <div className="project-board" aria-label="Project task board">
        {columns.length === 0 ? (
          <p className="admin-muted">
            {boardQuery.isLoading ? "Loading project board." : "No board columns are configured."}
          </p>
        ) : (
          columns.map((column) => (
            <section className="board-column" aria-labelledby={`board-column-${column.key}`} key={column.key}>
              <div className="board-column-header">
                <h3 id={`board-column-${column.key}`}>{column.label}</h3>
                <StatusBadge tone="neutral">{column.tasks.length}</StatusBadge>
              </div>
              <div className="board-task-list">
                {column.tasks.length === 0 ? (
                  <p className="admin-muted">No tasks.</p>
                ) : (
                  column.tasks.map((task, index) => (
                    <article className="board-task" aria-label={taskTitle(task)} key={task.id}>
                      <div className="board-task-main">
                        <strong>{taskTitle(task)}</strong>
                        <span>{taskMeta(task)}</span>
                      </div>
                      <StatusBadge tone={taskStatusTone(task.state ?? column.key)}>
                        {humanize(task.state ?? column.key)}
                      </StatusBadge>
                      <label className="field-control board-move-control">
                        <span>Move task</span>
                        <select
                          aria-label="Move task"
                          value={column.selectValue}
                          onChange={(event) => {
                            const targetColumn = columnFromSelectValue(columns, event.target.value);
                            moveTask.mutate({
                              taskId: task.id,
                              column: targetColumn.columnId,
                              sortOrder: nextSortOrder(columns, targetColumn.columnId, task.id)
                            });
                          }}
                          disabled={moveTask.isPending}
                        >
                          {columns.map((targetColumn) => (
                            <option key={targetColumn.key} value={targetColumn.selectValue}>
                              {targetColumn.label}
                            </option>
                          ))}
                        </select>
                      </label>
                      <span className="board-task-order">
                        <ArrowRight aria-hidden="true" size={14} />
                        {index + 1}
                      </span>
                    </article>
                  ))
                )}
              </div>
            </section>
          ))
        )}
      </div>

      {moveTask.isPending && (
        <p className="admin-muted project-loading-row">
          <Loader2 aria-hidden="true" size={14} />
          Moving task.
        </p>
      )}
    </section>
  );
}

function normalizeColumns(payload?: ProjectBoardPayload): NormalizedColumn[] {
  const columns =
    payload?.columns?.map((column, index) => {
      const columnId = numericColumnId(column.id);

      return {
        columnId,
        key: String(column.key ?? column.id ?? column.title ?? column.label ?? `column-${index}`),
        label:
          column.title ??
          column.label ??
          column.name ??
          humanize(String(column.key ?? column.id ?? "Column")),
        selectValue: columnId === null ? "" : String(columnId),
        tasks: column.tasks ?? []
      };
    }) ?? [];

  if ((payload?.unassigned_tasks ?? []).length > 0 || columns.length > 0) {
    columns.push({
      columnId: null,
      key: "unassigned",
      label: "Unassigned",
      selectValue: "",
      tasks: payload?.unassigned_tasks ?? []
    });
  }

  return columns;
}

function numericColumnId(value: string | number | undefined) {
  if (value === undefined || value === "") {
    return null;
  }

  const parsed = Number(value);
  return Number.isInteger(parsed) ? parsed : null;
}

function columnFromSelectValue(columns: NormalizedColumn[], value: string) {
  return columns.find((column) => column.selectValue === value) ?? {
    columnId: null,
    key: "unassigned",
    label: "Unassigned",
    selectValue: "",
    tasks: []
  };
}

function nextSortOrder(columns: NormalizedColumn[], targetColumnId: number | null, taskId: string | number) {
  const targetTasks = columns.find((column) => column.columnId === targetColumnId)?.tasks ?? [];
  return targetTasks.filter((task) => String(task.id) !== String(taskId)).length;
}

function taskTitle(task: ProjectTask) {
  return task.title ?? task.name ?? `Task ${task.id}`;
}

function taskMeta(task: ProjectTask) {
  return [
    task.assignee ?? task.assigned_to ?? task.owner,
    task.due_at || task.due_date ? `Due ${formatDate(task.due_at ?? task.due_date)}` : undefined
  ]
    .filter(Boolean)
    .join(" · ") || "No owner or due date";
}

function formatDate(value?: string) {
  if (!value) {
    return "Not set";
  }

  return new Intl.DateTimeFormat("en", { dateStyle: "medium" }).format(new Date(value));
}

function taskStatusTone(status?: string): StatusTone {
  if (status && ["done", "complete", "completed"].includes(status)) {
    return "ready";
  }

  if (status && ["blocked", "late", "overdue"].includes(status)) {
    return "blocked";
  }

  if (status && ["doing", "review", "open", "todo"].includes(status)) {
    return "review";
  }

  return "neutral";
}

function humanize(value: string) {
  return value.replace(/[_-]+/g, " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Project board request failed.";
}

