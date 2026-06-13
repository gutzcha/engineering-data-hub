/*
 * ===
 * File Summary
 * Path: frontend\src\features\projects\ProjectTimeline.tsx
 * Type: typescript
 * Purpose: Frontend feature module implementing business flows and UI surfaces.
 * Primary responsibilities:
 * - Domain behavior is summarized for fast onboarding and avoids full-file reread.
 * - Core symbols: ProjectTimeline
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
import { CalendarDays, GitBranch, Milestone } from "lucide-react";

import { StatusBadge } from "../../components/StatusBadge";
import { apiGet, apiPost } from "../../lib/api";
import type { ProjectSummary, ProjectTask } from "./ProjectBoard";

type ProjectMilestone = {
  id: string | number;
  title?: string;
  name?: string;
  due_at?: string;
  due_date?: string;
  date?: string;
  target_date?: string;
  completed?: boolean;
  completed_at?: string;
};

type ProjectDependency = {
  id?: string | number;
  task?: string | number;
  task_id?: string | number;
  depends_on?: string | number;
  depends_on_id?: string | number;
};

type TimelinePayload = {
  project?: ProjectSummary;
  milestones?: ProjectMilestone[];
  tasks?: ProjectTask[];
  dependencies?: ProjectDependency[];
};

type ProjectTimelineProps = {
  projectId: string | number;
  mode?: "timeline" | "dependencies";
};

export function ProjectTimeline({ projectId, mode = "timeline" }: ProjectTimelineProps) {
  const queryClient = useQueryClient();
  const timelineQuery = useQuery({
    queryKey: ["projects", projectId, "timeline"],
    queryFn: () => apiGet<TimelinePayload>(`/projects/${projectId}/timeline/`),
    enabled: Boolean(projectId)
  });

  const tasks = timelineQuery.data?.tasks ?? [];
  const milestones = timelineQuery.data?.milestones ?? [];
  const dependencies = timelineQuery.data?.dependencies ?? [];

  const addDependency = useMutation({
    mutationFn: ({ taskId, dependsOn }: { taskId: string | number; dependsOn: string | number }) =>
      apiPost<ProjectDependency>(`/project-tasks/${taskId}/dependencies/`, {
        depends_on: dependsOn
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["projects", projectId, "timeline"] });
    }
  });

  return (
    <section className="table-panel project-timeline-panel" aria-labelledby="project-timeline-title">
      <div className="panel-heading">
        <div>
          <p className="section-kicker">{mode === "dependencies" ? "Dependencies" : "Timeline"}</p>
          <h2 id="project-timeline-title">{mode === "dependencies" ? "Task Dependencies" : "Project Timeline"}</h2>
        </div>
        <StatusBadge tone={overdueCount(tasks, milestones) ? "blocked" : "active"}>
          {timelineQuery.isLoading ? "Loading" : `${tasks.length} Tasks`}
        </StatusBadge>
      </div>

      {(timelineQuery.error || addDependency.error) && (
        <div className="admin-alert project-inline-alert" role="alert">
          <strong>{addDependency.error ? "Dependency update failed" : "Timeline failed"}</strong>
          <span>{errorMessage(addDependency.error ?? timelineQuery.error)}</span>
        </div>
      )}

      <div className="project-timeline-body">
        {mode === "dependencies" ? (
          <DependencyEditor
            tasks={tasks}
            dependencies={dependencies}
            onAdd={(taskId, dependsOn) => addDependency.mutate({ taskId, dependsOn })}
            isSaving={addDependency.isPending}
          />
        ) : (
          <>
            <div className="timeline-milestones" aria-label="Milestones">
              {milestones.length === 0 ? (
                <p className="admin-muted">No milestones recorded.</p>
              ) : (
                milestones.map((milestone) => (
                  <div className={isMilestoneOverdue(milestone) ? "timeline-milestone overdue" : "timeline-milestone"} key={milestone.id}>
                    <Milestone aria-hidden="true" size={16} />
                    <div>
                      <strong>{milestone.title ?? milestone.name ?? `Milestone ${milestone.id}`}</strong>
                      <span>{formatDate(milestoneDate(milestone))}</span>
                    </div>
                    <StatusBadge tone={isMilestoneComplete(milestone) ? "ready" : isMilestoneOverdue(milestone) ? "blocked" : "neutral"}>
                      {isMilestoneComplete(milestone) ? "Done" : isMilestoneOverdue(milestone) ? "Overdue" : "Open"}
                    </StatusBadge>
                  </div>
                ))
              )}
            </div>

            <div className="timeline-list" role="list" aria-label="Timeline tasks">
              {tasks.length === 0 ? (
                <p className="admin-muted">{timelineQuery.isLoading ? "Loading timeline." : "No timeline tasks."}</p>
              ) : (
                tasks.map((task) => (
                  <article className={isTaskOverdue(task) ? "timeline-task overdue" : "timeline-task"} role="listitem" key={task.id}>
                    <CalendarDays aria-hidden="true" size={17} />
                    <div className="timeline-task-main">
                      <strong>{task.title ?? task.name ?? `Task ${task.id}`}</strong>
                      <span>
                        {formatDate(task.start_date)} to {formatDate(task.end_date ?? task.due_at ?? task.due_date)}
                      </span>
                      <small>{dependencySummary(task, dependencies)}</small>
                    </div>
                    <StatusBadge tone={isTaskOverdue(task) ? "blocked" : "neutral"}>
                      {isTaskOverdue(task) ? "Overdue" : task.state ?? task.column ?? "Scheduled"}
                    </StatusBadge>
                  </article>
                ))
              )}
            </div>
          </>
        )}
      </div>
    </section>
  );
}

function DependencyEditor({
  dependencies,
  isSaving,
  onAdd,
  tasks
}: {
  dependencies: ProjectDependency[];
  isSaving: boolean;
  onAdd: (taskId: string | number, dependsOn: string | number) => void;
  tasks: ProjectTask[];
}) {
  return (
    <div className="dependency-editor">
      {tasks.length === 0 ? (
        <p className="admin-muted">No tasks are available for dependency editing.</p>
      ) : (
        tasks.map((task) => (
          <article className="dependency-row" aria-label={`Dependencies for ${task.title ?? task.name ?? task.id}`} key={task.id}>
            <GitBranch aria-hidden="true" size={16} />
            <div>
              <strong>{task.title ?? task.name ?? `Task ${task.id}`}</strong>
              <span>{dependencySummary(task, dependencies)}</span>
            </div>
            <label className="field-control">
              <span>Add dependency</span>
              <select
                aria-label={`Add dependency for ${task.title ?? task.name ?? task.id}`}
                defaultValue=""
                disabled={isSaving}
                onChange={(event) => {
                  if (event.target.value) {
                    onAdd(task.id, event.target.value);
                    event.currentTarget.value = "";
                  }
                }}
              >
                <option value="">Select task</option>
                {tasks
                  .filter((candidate) => String(candidate.id) !== String(task.id))
                  .map((candidate) => (
                    <option key={candidate.id} value={candidate.id}>
                      {candidate.title ?? candidate.name ?? `Task ${candidate.id}`}
                    </option>
                  ))}
              </select>
            </label>
          </article>
        ))
      )}
    </div>
  );
}

function dependencySummary(task: ProjectTask, dependencies: ProjectDependency[]) {
  const taskDependencies = dependencies.filter(
    (dependency) => String(dependency.task ?? dependency.task_id) === String(task.id)
  );

  if (taskDependencies.length === 0) {
    return "No dependencies";
  }

  return `Depends on ${taskDependencies
    .map((dependency) => dependency.depends_on ?? dependency.depends_on_id)
    .join(", ")}`;
}

function overdueCount(tasks: ProjectTask[], milestones: ProjectMilestone[]) {
  return tasks.filter(isTaskOverdue).length + milestones.filter(isMilestoneOverdue).length;
}

function isTaskOverdue(task: ProjectTask) {
  const endValue = task.end_date ?? task.due_at ?? task.due_date;
  const state = task.state ?? task.column;
  return Boolean(endValue && new Date(endValue).getTime() < Date.now() && !["done", "complete", "completed"].includes(state ?? ""));
}

function isMilestoneOverdue(milestone: ProjectMilestone) {
  const dueValue = milestoneDate(milestone);
  return Boolean(dueValue && new Date(dueValue).getTime() < Date.now() && !isMilestoneComplete(milestone));
}

function isMilestoneComplete(milestone: ProjectMilestone) {
  return Boolean(milestone.completed || milestone.completed_at);
}

function milestoneDate(milestone: ProjectMilestone) {
  return milestone.target_date ?? milestone.due_at ?? milestone.due_date ?? milestone.date;
}

function formatDate(value?: string) {
  if (!value) {
    return "Not set";
  }

  return new Intl.DateTimeFormat("en", { dateStyle: "medium" }).format(new Date(value));
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Project timeline request failed.";
}

