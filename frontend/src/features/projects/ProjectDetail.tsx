import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileText, History, Link2, Loader2, PanelsTopLeft, Save } from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { StatusBadge } from "../../components/StatusBadge";
import { apiGet, apiPatch } from "../../lib/api";
import type { DocumentItem } from "../documents/DocumentPanel";
import { ProjectBoard } from "./ProjectBoard";
import type { ProjectBoardPayload, ProjectSummary } from "./ProjectBoard";
import { ProjectTimeline } from "./ProjectTimeline";
import { WorkloadView } from "./WorkloadView";

type TimelinePayload = {
  project?: ProjectDetailSummary;
  milestones?: unknown[];
  tasks?: unknown[];
  dependencies?: unknown[];
};

type ProjectDetailSummary = ProjectSummary & {
  description?: string;
  owner?: string | number | null;
  owner_username?: string | null;
  record?: string | number;
  start_date?: string | null;
  target_date?: string | null;
};

type ProjectDraft = {
  description: string;
  owner: string;
  status: string;
  target_date: string;
};

type ProjectTab = "overview" | "board" | "timeline" | "dependencies" | "linked" | "documents" | "audit";

type ProjectEvent = {
  id: string | number;
  action: string;
  actor_username?: string | null;
  task_title?: string | null;
  created_at?: string;
};

const tabs: Array<{ key: ProjectTab; label: string }> = [
  { key: "overview", label: "Overview" },
  { key: "board", label: "Board" },
  { key: "timeline", label: "Timeline" },
  { key: "dependencies", label: "Dependencies" },
  { key: "linked", label: "Linked Records" },
  { key: "documents", label: "Documents" },
  { key: "audit", label: "Audit" }
];

export function ProjectDetail() {
  const { projectId = "" } = useParams();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<ProjectTab>("overview");
  const [projectDraft, setProjectDraft] = useState<ProjectDraft>({
    description: "",
    owner: "",
    status: "planning",
    target_date: ""
  });
  const [projectDraftDirty, setProjectDraftDirty] = useState(false);

  const projectQuery = useQuery({
    queryKey: ["projects", projectId],
    queryFn: () => apiGet<ProjectDetailSummary>(`/projects/${projectId}/`),
    enabled: Boolean(projectId)
  });

  const boardQuery = useQuery({
    queryKey: ["projects", projectId, "board"],
    queryFn: () => apiGet<ProjectBoardPayload>(`/projects/${projectId}/board/`),
    enabled: Boolean(projectId)
  });

  const timelineQuery = useQuery({
    queryKey: ["projects", projectId, "timeline"],
    queryFn: () => apiGet<TimelinePayload>(`/projects/${projectId}/timeline/`),
    enabled: Boolean(projectId)
  });

  const project = useMemo<ProjectDetailSummary>(
    () => projectQuery.data ?? timelineQuery.data?.project ?? boardQuery.data?.project ?? { id: projectId },
    [boardQuery.data?.project, projectId, projectQuery.data, timelineQuery.data?.project]
  );
  const updateProject = useMutation({
    mutationFn: (draft: ProjectDraft) =>
      apiPatch<ProjectDetailSummary>(`/projects/${projectId}/`, {
        description: draft.description,
        owner: draft.owner ? Number(draft.owner) : null,
        status: draft.status,
        target_date: draft.target_date || null
    }),
    onSuccess: (updatedProject) => {
      setProjectDraft(projectDraftFromProject(updatedProject));
      setProjectDraftDirty(false);
      queryClient.setQueryData(["projects", projectId], updatedProject);
      void queryClient.invalidateQueries({ queryKey: ["projects"] });
      void queryClient.invalidateQueries({ queryKey: ["projects", "workload"] });
    }
  });

  useEffect(() => {
    setProjectDraftDirty(false);
  }, [projectId]);

  useEffect(() => {
    if (!projectDraftDirty) {
      setProjectDraft(projectDraftFromProject(project));
    }
  }, [project.description, project.owner, project.status, project.target_date, projectDraftDirty]);

  function updateProjectDraft(nextDraft: ProjectDraft) {
    setProjectDraftDirty(true);
    setProjectDraft(nextDraft);
  }

  function submitProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    updateProject.mutate(projectDraft);
  }

  const title = project.title ?? project.name ?? project.code ?? `Project ${project.id ?? projectId}`;
  const boardTaskCount =
    boardQuery.data?.columns?.reduce((total, column) => total + (column.tasks?.length ?? 0), 0) ?? 0;

  return (
    <div className="page-stack project-page">
      <section className="workspace-header" aria-labelledby="project-detail-title">
        <div>
          <p className="section-kicker">{project.code ?? `Project ${projectId}`}</p>
          <h1 id="project-detail-title">{title}</h1>
        </div>
        <StatusBadge tone={statusTone(project.status)}>{project.status ?? "Active"}</StatusBadge>
      </section>

      {(projectQuery.error || boardQuery.error || timelineQuery.error) && (
        <div className="admin-alert" role="alert">
          <strong>Project data partially unavailable</strong>
          <span>{errorMessage(projectQuery.error ?? boardQuery.error ?? timelineQuery.error)}</span>
        </div>
      )}

      <section className="admin-status-row" aria-label="Project summary">
        <SummaryMetric label="Board tasks" value={boardQuery.isLoading ? "Loading" : String(boardTaskCount)} />
        <SummaryMetric label="Timeline tasks" value={timelineQuery.isLoading ? "Loading" : String(timelineQuery.data?.tasks?.length ?? 0)} />
        <SummaryMetric label="Milestones" value={timelineQuery.isLoading ? "Loading" : String(timelineQuery.data?.milestones?.length ?? 0)} />
        <SummaryMetric label="Dependencies" value={timelineQuery.isLoading ? "Loading" : String(timelineQuery.data?.dependencies?.length ?? 0)} />
      </section>

      <nav className="segmented-tabs" aria-label="Project detail tabs">
        {tabs.map((tab) => (
          <button
            className={activeTab === tab.key ? "segmented-tab segmented-tab-active" : "segmented-tab"}
            type="button"
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      {activeTab === "overview" && (
        <div className="detail-grid">
          <OverviewPanel
            boardTaskCount={boardTaskCount}
            isLoading={boardQuery.isLoading || timelineQuery.isLoading}
            draft={projectDraft}
            isSaving={updateProject.isPending}
            onChange={updateProjectDraft}
            onSubmit={submitProject}
            project={project}
            saveError={updateProject.error}
            timelineTaskCount={timelineQuery.data?.tasks?.length ?? 0}
          />
          <WorkloadView compact />
        </div>
      )}

      {activeTab === "board" && <ProjectBoard projectId={projectId} />}
      {activeTab === "timeline" && <ProjectTimeline projectId={projectId} />}
      {activeTab === "dependencies" && <ProjectTimeline projectId={projectId} mode="dependencies" />}
      {activeTab === "linked" && <LinkedRecordsPanel recordId={timelineQuery.data?.project?.record} />}
      {activeTab === "documents" && <DocumentsPanel recordId={project.record ?? timelineQuery.data?.project?.record} />}
      {activeTab === "audit" && <AuditPanel projectId={projectId} />}
    </div>
  );
}

function OverviewPanel({
  boardTaskCount,
  draft,
  isLoading,
  isSaving,
  onChange,
  onSubmit,
  project,
  saveError,
  timelineTaskCount
}: {
  boardTaskCount: number;
  draft: ProjectDraft;
  isLoading: boolean;
  isSaving: boolean;
  onChange: (draft: ProjectDraft) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  project: ProjectDetailSummary;
  saveError: unknown;
  timelineTaskCount: number;
}) {
  return (
    <section className="table-panel detail-panel" aria-labelledby="project-overview-title">
      <div className="panel-heading">
        <div>
          <p className="section-kicker">Overview</p>
          <h2 id="project-overview-title">Project Summary</h2>
        </div>
        {isLoading ? <Loader2 aria-hidden="true" size={18} /> : <PanelsTopLeft aria-hidden="true" size={18} />}
      </div>
      <div className="record-panel-body project-overview-body">
        <div className="project-overview-summary">
          <dl className="definition-list">
            <div>
              <dt>Code</dt>
              <dd>{project.code ?? project.id ?? "Not recorded"}</dd>
            </div>
            <div>
              <dt>Status</dt>
              <dd>{project.status ?? "Active"}</dd>
            </div>
            <div>
              <dt>Owner</dt>
              <dd>{project.owner_username ?? project.owner ?? "Unassigned"}</dd>
            </div>
            <div>
              <dt>Target</dt>
              <dd>{formatDate(project.target_date)}</dd>
            </div>
            <div>
              <dt>Source record</dt>
              <dd>{project.record ?? "Not linked"}</dd>
            </div>
            <div>
              <dt>Board tasks</dt>
              <dd>{boardTaskCount}</dd>
            </div>
            <div>
              <dt>Timeline tasks</dt>
              <dd>{timelineTaskCount}</dd>
            </div>
          </dl>
        </div>
        <form className="admin-form-grid project-overview-form" onSubmit={onSubmit}>
          <label className="field-control">
            <span>Project Status</span>
            <select
              aria-label="Project Status"
              value={draft.status}
              onChange={(event) => onChange({ ...draft, status: event.target.value })}
            >
              <option value="planning">Planning</option>
              <option value="active">Active</option>
              <option value="complete">Complete</option>
              <option value="archived">Archived</option>
            </select>
          </label>
          <label className="field-control">
            <span>Owner User ID</span>
            <input
              aria-label="Owner User ID"
              inputMode="numeric"
              min="1"
              type="number"
              value={draft.owner}
              onChange={(event) => onChange({ ...draft, owner: event.target.value })}
            />
          </label>
          <label className="field-control">
            <span>Target Date</span>
            <input
              aria-label="Target Date"
              type="date"
              value={draft.target_date}
              onChange={(event) => onChange({ ...draft, target_date: event.target.value })}
            />
          </label>
          <label className="field-control field-control-wide">
            <span>Description</span>
            <textarea
              aria-label="Description"
              rows={3}
              value={draft.description}
              onChange={(event) => onChange({ ...draft, description: event.target.value })}
            />
          </label>
          <button className="button button-primary" type="submit" disabled={isSaving}>
            <Save aria-hidden="true" size={16} />
            {isSaving ? "Saving" : "Save Project"}
          </button>
        </form>
        {saveError ? (
          <div className="admin-alert" role="alert">
            <strong>Project was not saved</strong>
            <span>{errorMessage(saveError)}</span>
          </div>
        ) : null}
      </div>
    </section>
  );
}

function projectDraftFromProject(project: ProjectDetailSummary): ProjectDraft {
  return {
    description: project.description ?? "",
    owner: project.owner === undefined || project.owner === null ? "" : String(project.owner),
    status: project.status ?? "planning",
    target_date: project.target_date ?? ""
  };
}

function LinkedRecordsPanel({ recordId }: { recordId?: string | number }) {
  return (
    <section className="table-panel detail-panel" aria-labelledby="linked-records-title">
      <div className="panel-heading">
        <div>
          <p className="section-kicker">Linked records</p>
          <h2 id="linked-records-title">Linked Records</h2>
        </div>
        <Link2 aria-hidden="true" size={18} />
      </div>
      <div className="record-panel-body link-list">
        {recordId ? (
          <Link to={`/records/${recordId}`}>
            <strong>Source record {recordId}</strong>
            <span>Project record link</span>
          </Link>
        ) : (
          <p className="admin-muted">No linked record data is available for this project.</p>
        )}
      </div>
    </section>
  );
}

function DocumentsPanel({ recordId }: { recordId?: string | number }) {
  const documentsQuery = useQuery({
    queryKey: ["project-documents", recordId],
    queryFn: () => apiGet<DocumentItem[]>(`/documents/?owner_record=${recordId}`),
    enabled: recordId !== undefined && recordId !== null && String(recordId).length > 0
  });
  const documents = documentsQuery.data ?? [];

  return (
    <section className="table-panel detail-panel" aria-labelledby="project-documents-title">
      <div className="panel-heading">
        <div>
          <p className="section-kicker">Documents</p>
          <h2 id="project-documents-title">Documents</h2>
        </div>
        <FileText aria-hidden="true" size={18} />
      </div>
      <div className="record-panel-body document-list" role="list" aria-label="Project documents">
        {!recordId ? (
          <p className="admin-muted">This project has no linked source record for document lookup.</p>
        ) : documentsQuery.error ? (
          <div className="admin-alert" role="alert">
            <strong>Project documents failed</strong>
            <span>{errorMessage(documentsQuery.error)}</span>
          </div>
        ) : documentsQuery.isLoading ? (
          <p className="admin-muted">Loading project documents.</p>
        ) : documents.length ? (
          documents.map((document) => (
            <Link className="document-item" role="listitem" to={`/documents/${document.id}`} key={document.id}>
              <div className="document-main">
                <strong>{document.title ?? document.name ?? document.filename ?? document.id}</strong>
                <span>{document.document_type ?? "document"}</span>
              </div>
              <StatusBadge tone={document.state === "released" ? "ready" : "review"}>
                {document.state ?? document.status ?? "draft"}
              </StatusBadge>
            </Link>
          ))
        ) : (
          <p className="admin-muted">No controlled documents are linked to this project record.</p>
        )}
      </div>
    </section>
  );
}

function AuditPanel({ projectId }: { projectId: string }) {
  const eventsQuery = useQuery({
    queryKey: ["projects", projectId, "events"],
    queryFn: () => apiGet<ProjectEvent[]>(`/projects/${projectId}/events/`),
    enabled: Boolean(projectId)
  });
  const events = eventsQuery.data ?? [];

  return (
    <section className="table-panel detail-panel" aria-labelledby="project-audit-title">
      <div className="panel-heading">
        <div>
          <p className="section-kicker">Audit</p>
          <h2 id="project-audit-title">Audit</h2>
        </div>
        <History aria-hidden="true" size={18} />
      </div>
      <div className="record-panel-body event-list" role="list" aria-label="Project audit events">
        {eventsQuery.error ? (
          <div className="admin-alert" role="alert">
            <strong>Project audit failed</strong>
            <span>{errorMessage(eventsQuery.error)}</span>
          </div>
        ) : eventsQuery.isLoading ? (
          <p className="admin-muted">Loading project audit events.</p>
        ) : events.length ? (
          events.map((event) => (
            <article className="event-item" role="listitem" key={event.id}>
              <strong>{humanize(event.action)}</strong>
              <span>{event.task_title ?? event.actor_username ?? "Project"}</span>
              <span>{formatDate(event.created_at)}</span>
            </article>
          ))
        ) : (
          <p className="admin-muted">No project audit events are recorded yet.</p>
        )}
      </div>
    </section>
  );
}

function SummaryMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="admin-stat">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function statusTone(status?: string) {
  if (status === "complete" || status === "released" || status === "active") {
    return "ready";
  }

  if (status === "blocked") {
    return "blocked";
  }

  return "review";
}

function formatDate(value?: string | null) {
  if (!value) {
    return "Not set";
  }

  return new Intl.DateTimeFormat("en", { dateStyle: "medium" }).format(new Date(value));
}

function humanize(value?: string | null) {
  if (!value) {
    return "Not recorded";
  }
  return value.replace(/[_\.]+/g, " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Project request failed.";
}
