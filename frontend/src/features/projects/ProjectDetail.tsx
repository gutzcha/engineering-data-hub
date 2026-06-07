import { useQuery } from "@tanstack/react-query";
import { ClipboardList, FileText, History, Link2, Loader2, PanelsTopLeft } from "lucide-react";
import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { StatusBadge } from "../../components/StatusBadge";
import { apiGet } from "../../lib/api";
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

type ProjectDetailSummary = ProjectSummary & { record?: string | number };

type ProjectTab = "overview" | "board" | "timeline" | "dependencies" | "linked" | "documents" | "audit";

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
  const [activeTab, setActiveTab] = useState<ProjectTab>("overview");

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
    () => timelineQuery.data?.project ?? boardQuery.data?.project ?? { id: projectId },
    [boardQuery.data?.project, projectId, timelineQuery.data?.project]
  );

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

      {(boardQuery.error || timelineQuery.error) && (
        <div className="admin-alert" role="alert">
          <strong>Project data partially unavailable</strong>
          <span>{errorMessage(boardQuery.error ?? timelineQuery.error)}</span>
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
            project={project}
            timelineTaskCount={timelineQuery.data?.tasks?.length ?? 0}
          />
          <WorkloadView compact />
        </div>
      )}

      {activeTab === "board" && <ProjectBoard projectId={projectId} />}
      {activeTab === "timeline" && <ProjectTimeline projectId={projectId} />}
      {activeTab === "dependencies" && <ProjectTimeline projectId={projectId} mode="dependencies" />}
      {activeTab === "linked" && <LinkedRecordsPanel recordId={timelineQuery.data?.project?.record} />}
      {activeTab === "documents" && <DocumentsPanel />}
      {activeTab === "audit" && <AuditPanel />}
    </div>
  );
}

function OverviewPanel({
  boardTaskCount,
  isLoading,
  project,
  timelineTaskCount
}: {
  boardTaskCount: number;
  isLoading: boolean;
  project: ProjectDetailSummary;
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
      <div className="record-panel-body">
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
    </section>
  );
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

function DocumentsPanel() {
  return (
    <section className="table-panel detail-panel" aria-labelledby="project-documents-title">
      <div className="panel-heading">
        <div>
          <p className="section-kicker">Documents</p>
          <h2 id="project-documents-title">Documents</h2>
        </div>
        <FileText aria-hidden="true" size={18} />
      </div>
      <div className="record-panel-body document-list">
        <p className="admin-muted">Project documents are not available from the current project endpoints.</p>
      </div>
    </section>
  );
}

function AuditPanel() {
  return (
    <section className="table-panel detail-panel" aria-labelledby="project-audit-title">
      <div className="panel-heading">
        <div>
          <p className="section-kicker">Audit</p>
          <h2 id="project-audit-title">Audit</h2>
        </div>
        <History aria-hidden="true" size={18} />
      </div>
      <div className="record-panel-body event-list" role="list">
        <p className="admin-muted">Project audit events are not available from the current project endpoints.</p>
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

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Project request failed.";
}
