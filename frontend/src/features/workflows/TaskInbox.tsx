import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, ClipboardCheck, Loader2, SlidersHorizontal } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { DataTable } from "../../components/DataTable";
import { StatusBadge } from "../../components/StatusBadge";
import type { StatusTone } from "../../components/StatusBadge";
import { apiGet, apiPost } from "../../lib/api";

export type WorkflowTask = {
  id: string | number;
  title?: string;
  name?: string;
  summary?: string;
  state?: string;
  status?: string;
  assigned_to?: string | { id?: string | number; username?: string; name?: string; email?: string } | null;
  assignee?: string | { id?: string | number; username?: string; name?: string; email?: string } | null;
  assignee_user?: string | number | { id?: string | number; username?: string; name?: string; email?: string } | null;
  assigned_role?: string;
  assignee_role?: string | { id?: string | number; name?: string; label?: string } | null;
  role?: string;
  due_at?: string;
  due_date?: string;
  related_object_type?: string;
  object_type?: string;
  related_object_id?: string | number | null;
  related_record?: string | number | { id?: string | number; code?: string; title?: string } | null;
  related_document?: string | number | { id?: string | number; title?: string } | null;
  related_project?: string | number | { id?: string | number; title?: string } | null;
  record?: string | number | { id?: string | number; code?: string; title?: string } | null;
  transition_key?: string;
  transition_label?: string;
  created_at?: string;
};

type CurrentUser = {
  id?: string | number;
  username?: string;
  name?: string;
  email?: string;
  roles?: Array<string | { id?: string | number; name?: string; label?: string }>;
  groups?: Array<string | { id?: string | number; name?: string; label?: string }>;
};

type AssignmentFilter = "all" | "me" | "role";
type DueFilter = "all" | "overdue";

type TaskInboxProps = {
  currentUser?: string;
  currentUserId?: string | number;
  currentRoles?: string[];
};

export function TaskInbox({
  currentUser = "me",
  currentUserId,
  currentRoles = ["Engineering", "Quality", "Approver"]
}: TaskInboxProps) {
  const queryClient = useQueryClient();
  const [assignment, setAssignment] = useState<AssignmentFilter>("all");
  const [due, setDue] = useState<DueFilter>("all");
  const [objectType, setObjectType] = useState("all");
  const [state, setState] = useState("all");
  const [query, setQuery] = useState("");

  const tasksQuery = useQuery({
    queryKey: ["workflow-tasks", "open"],
    queryFn: () => apiGet<WorkflowTask[]>("/workflow-tasks/?state=open")
  });

  const currentUserQuery = useQuery({
    queryKey: ["accounts", "me"],
    queryFn: () => apiGet<CurrentUser>("/accounts/me/")
  });

  const completeTask = useMutation({
    mutationFn: (taskId: string | number) =>
      apiPost<WorkflowTask>(`/workflow-tasks/${taskId}/complete/`, {}),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["workflow-tasks", "open"] });
    }
  });

  const tasks = tasksQuery.data ?? [];
  const me = currentUserQuery.data;
  const effectiveUserId = currentUserId ?? me?.id;
  const effectiveUserName = me?.username ?? me?.name ?? me?.email ?? currentUser;
  const effectiveRoles = uniqueOptions([...currentRoles, ...rolesFromUser(me)]);
  const objectTypes = uniqueOptions(tasks.map(taskObjectType));
  const states = uniqueOptions(tasks.map(taskState));
  const filteredTasks = useMemo(
    () =>
      tasks.filter((task) => {
        if (assignment === "me" && !isAssignedToUser(task, effectiveUserName, effectiveUserId)) {
          return false;
        }

        if (assignment === "role" && !isAssignedToRole(task, effectiveRoles)) {
          return false;
        }

        if (due === "overdue" && !isOverdue(task)) {
          return false;
        }

        if (objectType !== "all" && taskObjectType(task) !== objectType) {
          return false;
        }

        if (state !== "all" && taskState(task) !== state) {
          return false;
        }

        const searchable = [
          taskTitle(task),
          taskObjectType(task),
          taskState(task),
          assigneeName(task),
          taskRole(task)
        ]
          .join(" ")
          .toLowerCase();

        return searchable.includes(query.trim().toLowerCase());
      }),
    [assignment, due, effectiveRoles, effectiveUserId, effectiveUserName, objectType, query, state, tasks]
  );

  return (
    <div className="page-stack workflow-page">
      <section className="workspace-header" aria-labelledby="task-inbox-title">
        <div>
          <p className="section-kicker">Review queues and assignments</p>
          <h1 id="task-inbox-title">Task Inbox</h1>
        </div>
        <StatusBadge tone={filteredTasks.length ? "review" : "ready"}>
          {tasksQuery.isLoading ? "Loading" : `${filteredTasks.length} Tasks`}
        </StatusBadge>
      </section>

      <section className="filter-panel" aria-label="Task inbox filters">
        <div className="search-form">
          <label className="field-control field-control-wide">
            <span>Search tasks</span>
            <input
              aria-label="Search tasks"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Title, assignee, state, object"
            />
          </label>
        </div>
        <div className="filter-grid">
          <label className="field-control">
            <span>Assignment</span>
            <select
              aria-label="Assignment"
              value={assignment}
              onChange={(event) => setAssignment(event.target.value as AssignmentFilter)}
            >
              <option value="all">All assignments</option>
              <option value="me">Assigned to me</option>
              <option value="role">Assigned to my role</option>
            </select>
          </label>
          <label className="field-control">
            <span>Due</span>
            <select
              aria-label="Due"
              value={due}
              onChange={(event) => setDue(event.target.value as DueFilter)}
            >
              <option value="all">All due dates</option>
              <option value="overdue">Overdue</option>
            </select>
          </label>
          <label className="field-control">
            <span>Related object type</span>
            <select
              aria-label="Related object type"
              value={objectType}
              onChange={(event) => setObjectType(event.target.value)}
            >
              <option value="all">All object types</option>
              {objectTypes.map((type) => (
                <option key={type} value={type}>
                  {humanize(type)}
                </option>
              ))}
            </select>
          </label>
          <label className="field-control">
            <span>State</span>
            <select
              aria-label="State"
              value={state}
              onChange={(event) => setState(event.target.value)}
            >
              <option value="all">All states</option>
              {states.map((taskStateValue) => (
                <option key={taskStateValue} value={taskStateValue}>
                  {humanize(taskStateValue)}
                </option>
              ))}
            </select>
          </label>
        </div>
      </section>

      {(tasksQuery.error || completeTask.error) && (
        <div className="admin-alert" role="alert">
          <strong>{completeTask.error ? "Task completion failed" : "Task inbox failed"}</strong>
          <span>{errorMessage(completeTask.error ?? tasksQuery.error)}</span>
        </div>
      )}

      <section className="table-panel" aria-labelledby="task-table-title">
        <div className="panel-heading">
          <div>
            <p className="section-kicker">Open work</p>
            <h2 id="task-table-title">Workflow Tasks</h2>
          </div>
          <SlidersHorizontal aria-hidden="true" size={18} />
        </div>
        <DataTable
          data={filteredTasks}
          emptyMessage={tasksQuery.isLoading ? "Loading tasks." : "No tasks match these filters."}
          columns={[
            {
              accessorKey: "title",
              header: "Task",
              cell: ({ row }) => (
                <div className="task-title-cell">
                  <strong>{taskTitle(row.original)}</strong>
                  <span>{taskSubtitle(row.original)}</span>
                </div>
              )
            },
            {
              id: "assignment",
              header: "Assignment",
              cell: ({ row }) => (
                <span>{[assigneeName(row.original), taskRole(row.original)].filter(Boolean).join(" / ") || "Unassigned"}</span>
              )
            },
            {
              id: "due",
              header: "Due",
              cell: ({ row }) => (
                <StatusBadge tone={isOverdue(row.original) ? "blocked" : "neutral"}>
                  {formatDate(row.original.due_at ?? row.original.due_date)}
                </StatusBadge>
              )
            },
            {
              id: "state",
              header: "State",
              cell: ({ row }) => (
                <StatusBadge tone={statusTone(taskState(row.original))}>
                  {humanize(taskState(row.original))}
                </StatusBadge>
              )
            },
            {
              id: "actions",
              header: "Actions",
              cell: ({ row }) => (
                <div className="record-action-row">
                  {taskHref(row.original) && (
                    <Link className="text-link" to={taskHref(row.original) ?? "#"}>
                      Open
                    </Link>
                  )}
                  <button
                    className="button button-secondary"
                    type="button"
                    onClick={() => completeTask.mutate(row.original.id)}
                    disabled={completeTask.isPending}
                  >
                    {completeTask.isPending ? (
                      <Loader2 aria-hidden="true" size={16} />
                    ) : (
                      <CheckCircle2 aria-hidden="true" size={16} />
                    )}
                    Complete
                  </button>
                </div>
              )
            }
          ]}
        />
      </section>
    </div>
  );
}

function taskTitle(task: WorkflowTask) {
  return task.title ?? task.name ?? task.summary ?? `Task ${task.id}`;
}

function taskSubtitle(task: WorkflowTask) {
  return [
    humanize(taskObjectType(task)),
    taskRelatedId(task) ? `#${taskRelatedId(task)}` : undefined,
    task.transition_label ?? task.transition_key
  ]
    .filter(Boolean)
    .join(" · ");
}

function taskState(task: WorkflowTask) {
  return task.state ?? task.status ?? "open";
}

function taskObjectType(task: WorkflowTask) {
  if (task.related_document !== undefined && task.related_document !== null) {
    return "document";
  }

  if (task.related_project !== undefined && task.related_project !== null && task.related_project !== "") {
    return "project";
  }

  if (task.related_record !== undefined && task.related_record !== null) {
    return "record";
  }

  return task.related_object_type ?? task.object_type ?? "record";
}

function assigneeName(task: WorkflowTask) {
  const assignee = task.assigned_to ?? task.assignee ?? task.assignee_user;

  if (!assignee) {
    return "";
  }

  if (typeof assignee === "string") {
    return assignee;
  }

  if (typeof assignee === "number") {
    return `User ${assignee}`;
  }

  return assignee.username ?? assignee.name ?? assignee.email ?? String(assignee.id ?? "");
}

function taskRole(task: WorkflowTask) {
  const role = task.assignee_role ?? task.assigned_role ?? task.role;

  if (!role) {
    return "";
  }

  if (typeof role === "string") {
    return role;
  }

  return role.name ?? role.label ?? String(role.id ?? "");
}

function isAssignedToUser(task: WorkflowTask, currentUser: string, currentUserId?: string | number) {
  if (currentUserId !== undefined && task.assignee_user !== undefined && task.assignee_user !== null) {
    const assigneeId =
      typeof task.assignee_user === "object" ? task.assignee_user.id : task.assignee_user;
    return String(assigneeId) === String(currentUserId);
  }

  return assigneeName(task).toLowerCase() === currentUser.toLowerCase();
}

function isAssignedToRole(task: WorkflowTask, currentRoles: string[]) {
  const role = taskRole(task).toLowerCase();
  return currentRoles.some((currentRole) => currentRole.toLowerCase() === role);
}

function isOverdue(task: WorkflowTask) {
  const dueValue = task.due_at ?? task.due_date;
  return Boolean(dueValue && new Date(dueValue).getTime() < Date.now());
}

function taskHref(task: WorkflowTask) {
  const objectType = taskObjectType(task);
  const objectId = taskRelatedId(task);

  if (!objectId) {
    return undefined;
  }

  if (objectType === "document") {
    return `/documents/${objectId}`;
  }

  if (objectType === "project") {
    return `/projects/${objectId}`;
  }

  return `/records/${objectId}`;
}

function taskRelatedId(task: WorkflowTask) {
  const relatedRecord = relationId(task.related_record);
  const relatedDocument = relationId(task.related_document);
  const relatedProject = relationId(task.related_project);
  const record = relationId(task.record);

  return (
    task.related_object_id ??
    relatedDocument ??
    relatedProject ??
    relatedRecord ??
    record
  );
}

function relationId(
  relation?: string | number | { id?: string | number } | null
) {
  if (relation === undefined || relation === null || relation === "") {
    return undefined;
  }

  return typeof relation === "object" ? relation.id : relation;
}

function rolesFromUser(user?: CurrentUser) {
  return [...(user?.roles ?? []), ...(user?.groups ?? [])]
    .map((role) => {
      if (typeof role === "string") {
        return role;
      }

      return role.name ?? role.label ?? "";
    })
    .filter(Boolean);
}

function uniqueOptions(values: string[]) {
  return Array.from(new Set(values.filter(Boolean))).sort((first, second) =>
    first.localeCompare(second)
  );
}

function formatDate(value?: string) {
  if (!value) {
    return "No due date";
  }

  return new Intl.DateTimeFormat("en", { dateStyle: "medium" }).format(new Date(value));
}

function statusTone(status: string): StatusTone {
  if (["done", "complete", "completed", "released"].includes(status)) {
    return "ready";
  }

  if (["blocked", "failed", "overdue"].includes(status)) {
    return "blocked";
  }

  if (["open", "review", "pending"].includes(status)) {
    return "review";
  }

  return "neutral";
}

function humanize(value: string) {
  return value.replace(/[_-]+/g, " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Workflow task request failed.";
}
