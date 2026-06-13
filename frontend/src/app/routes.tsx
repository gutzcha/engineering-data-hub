/*
 * ===
 * File Summary
 * Path: frontend\src\app\routes.tsx
 * Type: typescript
 * Purpose: Frontend application shell and route composition for authenticated screens.
 * Primary responsibilities:
 * - Domain behavior is summarized for fast onboarding and avoids full-file reread.
 * - Core symbols: NavigationItem, navigationItems, AppRoutes
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

import {
  BarChart3,
  ClipboardCheck,
  Database,
  Download,
  FileText,
  FolderKanban,
  History,
  Home,
  Plus,
  Search,
  Settings,
  SlidersHorizontal,
  UploadCloud
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { Link, Navigate, Route, Routes, useNavigate, useParams } from "react-router-dom";

import { StatusBadge } from "../components/StatusBadge";
import { ConfigWorkspace } from "../features/admin-config/ConfigWorkspace";
import { LoginPage } from "../features/auth/LoginPage";
import { AuditTimeline } from "../features/audit/AuditTimeline";
import { DashboardPage } from "../features/dashboards/DashboardPage";
import {
  DocumentDetailPage,
  DocumentLibraryPage
} from "../features/documents/DocumentPanel";
import { FolderReviewInbox } from "../features/folders/FolderReviewInbox";
import { ImportWizard } from "../features/imports/ImportWizard";
import { ProjectDetail } from "../features/projects/ProjectDetail";
import { ProjectList } from "../features/projects/ProjectList";
import { RecordCreate } from "../features/records/RecordCreate";
import { RecordDetail } from "../features/records/RecordDetail";
import { RecordList } from "../features/records/RecordList";
import { SearchPage } from "../features/search/SearchPage";
import { buildSearchPageUrl } from "../features/search/searchUrl";
import { TaskInbox } from "../features/workflows/TaskInbox";
import { apiGet } from "../lib/api";

export type NavigationItem = {
  label: string;
  path: string;
  icon: LucideIcon;
  description: string;
};

export const navigationItems: NavigationItem[] = [
  {
    label: "Home",
    path: "/",
    icon: Home,
    description: "Portfolio health and urgent work"
  },
  {
    label: "Records",
    path: "/records",
    icon: Database,
    description: "Material, trial, and test records"
  },
  {
    label: "Projects",
    path: "/projects",
    icon: FolderKanban,
    description: "Engineering project workspaces"
  },
  {
    label: "Imports",
    path: "/imports",
    icon: UploadCloud,
    description: "Excel and CSV intake"
  },
  {
    label: "Documents",
    path: "/documents",
    icon: FileText,
    description: "Specifications and controlled files"
  },
  {
    label: "Search",
    path: "/search",
    icon: Search,
    description: "Cross-system discovery"
  },
  {
    label: "Dashboards",
    path: "/dashboards",
    icon: BarChart3,
    description: "Operational reporting"
  },
  {
    label: "Audit",
    path: "/audit",
    icon: History,
    description: "Append-only system history"
  },
  {
    label: "Tasks",
    path: "/tasks",
    icon: ClipboardCheck,
    description: "Review queues and assignments"
  },
  {
    label: "Admin",
    path: "/admin",
    icon: Settings,
    description: "Users, taxonomies, and controls"
  }
];

type HomeMetricCard = {
  key: string;
  label: string;
  value: number;
  filter: {
    status: string;
  };
};

type HomeRecord = {
  id: string;
  code?: string;
  title?: string;
  status?: string;
  object_type_key?: string;
  project_id?: string;
};

type HomeOverviewPayload = {
  cards: HomeMetricCard[];
  recent_records: HomeRecord[];
};

const statusLabel: Record<string, string> = {
  active: "Active",
  ready: "Ready",
  review: "Review",
  blocked: "Blocked",
  released: "Ready",
  draft: "Ready",
  completed: "Ready",
  complete: "Ready",
  neutral: "Ready",
  default: "Ready"
};

const statusTone: Record<string, "active" | "review" | "blocked" | "ready" | "neutral"> = {
  active: "active" as const,
  review: "review" as const,
  blocked: "blocked" as const,
  ready: "ready" as const,
  released: "ready" as const,
  draft: "ready" as const,
  completed: "ready" as const,
  complete: "ready" as const,
  neutral: "neutral" as const,
  default: "neutral" as const
};

function HomePage() {
  const navigate = useNavigate();
  const homeQuery = useQuery({
    queryKey: ["reports", "home-overview"],
    queryFn: () => apiGet<HomeOverviewPayload>("/dashboards/home-overview/?limit=10")
  });

  const cards = homeQuery.data?.cards ?? [];
  const recentRecords = homeQuery.data?.recent_records ?? [];

  function navigateToSearch(card: HomeMetricCard) {
    navigate(buildSearchPageUrl({ type: "records", status: card.filter?.status }));
  }

  function exportRecentRecords() {
    if (homeQuery.isLoading || homeQuery.isError || recentRecords.length === 0) {
      return;
    }

    const rows = [
      ["Code", "Title", "Status", "Type"],
      ...recentRecords.map((record) => [
        record.code ?? record.id,
        record.title ?? "",
        record.status ?? "",
        record.object_type_key ?? ""
      ])
    ];
    const csv = rows.map((row) => row.map(csvCell).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "operational-overview-records.csv";
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="page-stack">
      <section className="workspace-header" aria-labelledby="overview-title">
        <div>
          <p className="section-kicker">Plastic Engineering Data Hub</p>
          <h1 id="overview-title">Operational Overview</h1>
        </div>
        <div className="header-actions">
          <button
            className="button button-secondary"
            type="button"
            onClick={exportRecentRecords}
            disabled={homeQuery.isLoading || homeQuery.isError || recentRecords.length === 0}
          >
            <Download aria-hidden="true" size={16} />
            Export recent records
          </button>
          <Link className="button button-primary" to="/records/new">
            <Plus aria-hidden="true" size={16} />
            New Record
          </Link>
        </div>
      </section>

      <section className="metrics-grid" aria-label="Workspace metrics">
        {homeQuery.isLoading && (
          <>
            <article className="metric">
              <Metric label="Loading" value="..." status="neutral" />
            </article>
            <article className="metric">
              <Metric label="Loading" value="..." status="neutral" />
            </article>
            <article className="metric">
              <Metric label="Loading" value="..." status="neutral" />
            </article>
            <article className="metric">
              <Metric label="Loading" value="..." status="neutral" />
            </article>
          </>
        )}

        {homeQuery.isError && (
          <article className="metric">
            <span>Failed to load overview</span>
            <strong>—</strong>
            <StatusBadge tone="neutral">Unavailable</StatusBadge>
          </article>
        )}

        {!homeQuery.isLoading &&
          !homeQuery.isError &&
          cards.map((card) => (
            <button
              className="metric"
              key={card.key}
              type="button"
              aria-label={`Open search filtered by ${card.label}`}
              onClick={() => navigateToSearch(card)}
            >
              <Metric
                label={card.label}
                value={String(card.value)}
                status={statusTone[card.filter?.status] ?? statusTone.default}
              />
            </button>
          ))}

        {!homeQuery.isLoading &&
          !homeQuery.isError &&
          cards.length === 0 && (
            <article className="metric">
              <span>No metrics</span>
              <strong>0</strong>
              <StatusBadge tone="neutral">No data</StatusBadge>
            </article>
          )}
      </section>

      <section className="table-panel" aria-labelledby="queue-title">
        <div className="panel-heading">
          <div>
            <p className="section-kicker">Queue</p>
            <h2 id="queue-title">Recent Record Activity</h2>
          </div>
          <StatusBadge tone="review">
            {homeQuery.isLoading ? "Loading" : `${recentRecords.length} items`}
          </StatusBadge>
        </div>
        {homeQuery.isLoading ? (
          <p className="admin-muted">Loading recent records...</p>
        ) : recentRecords.length === 0 ? (
          <p className="admin-muted">No recent records match your current visibility filters.</p>
        ) : (
          <div className="search-result-list" role="list" aria-label="Recent records">
            {recentRecords.map((record) => (
              <Link
                className="search-result"
                to={homeRecordUrl(record)}
                key={record.id}
                aria-label={`Open ${record.code ?? record.id} ${record.title ?? ""}`}
              >
                <div>
                  <strong>{record.code || record.id}</strong>
                  <small>
                    {record.title ?? "Untitled"}
                    {record.object_type_key ? ` · ${record.object_type_key}` : ""}
                  </small>
                </div>
                <StatusBadge tone={statusTone[record.status ?? ""] ?? "neutral"}>
                  {statusLabel[record.status ?? ""] ?? statusLabel.default}
                </StatusBadge>
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function Metric({
  label,
  value,
  status
}: {
  label: string;
  value: string;
  status: "active" | "ready" | "review" | "blocked" | "neutral";
}) {
  return (
    <>
      <span>{label}</span>
      <strong>{value}</strong>
      <StatusBadge tone={status}>{statusLabelForMetric(status)}</StatusBadge>
    </>
  );
}

function csvCell(value: string) {
  const escaped = value.replace(/"/g, '""');
  return `"${escaped}"`;
}

function statusLabelForMetric(status: "active" | "ready" | "review" | "blocked" | "neutral") {
  const labels = {
    active: "Active",
    ready: "Ready",
    review: "Review",
    blocked: "Blocked",
    neutral: "Ready"
  };

  return labels[status];
}

function homeRecordUrl(record: HomeRecord) {
  if (record.object_type_key === "project" && record.project_id) {
    return `/projects/${record.project_id}`;
  }

  return `/records/${record.id}`;
}

function PlaceholderPage({ item }: { item: NavigationItem }) {
  const Icon = item.icon;

  return (
    <div className="page-stack">
      <section className="workspace-header" aria-labelledby={`${item.label}-title`}>
        <div>
          <p className="section-kicker">{item.description}</p>
          <h1 id={`${item.label}-title`}>{item.label}</h1>
        </div>
        <Link className="button button-secondary" to={buildSearchPageUrl({ q: item.label })}>
          <SlidersHorizontal aria-hidden="true" size={16} />
          Open Search Hub
        </Link>
      </section>
      <section className="empty-state">
        <Icon aria-hidden="true" size={28} />
        <div>
          <h2>{item.label} Workspace</h2>
          <p>
            No workspace items are queued here yet. Assigned records, documents,
            and reviews will appear as work moves through the hub.
          </p>
        </div>
      </section>
    </div>
  );
}

function SearchTargetPlaceholder({
  description,
  idParam,
  label
}: {
  description: string;
  idParam: string;
  label: string;
}) {
  const params = useParams();
  const id = params[idParam] ?? "selected";

  return (
    <div className="page-stack">
      <section className="workspace-header" aria-labelledby={`${label}-detail-title`}>
        <div>
          <p className="section-kicker">{description}</p>
          <h1 id={`${label}-detail-title`}>
            {label} {id}
          </h1>
        </div>
      </section>
      <section className="empty-state">
        <Search aria-hidden="true" size={28} />
        <div>
          <h2>{label} search target</h2>
          <p>
            This route preserves navigation from unified search while the full
            workspace detail surface is completed.
          </p>
        </div>
      </section>
    </div>
  );
}

function TaskWorkspace() {
  return (
    <div className="page-stack">
      <TaskInbox />
      <section className="table-panel" aria-labelledby="folder-review-access-title">
        <div className="panel-heading">
          <div>
            <p className="section-kicker">Folder review</p>
            <h2 id="folder-review-access-title">Managed Folder Review</h2>
          </div>
          <Link className="button button-secondary" to="/tasks/folder-events">
            Open Inbox
          </Link>
        </div>
      </section>
    </div>
  );
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/records" element={<RecordList />} />
      <Route path="/records/new" element={<RecordCreate />} />
      <Route path="/records/:recordId" element={<RecordDetail />} />
      <Route path="/projects" element={<ProjectList />} />
      <Route path="/projects/:projectId" element={<ProjectDetail />} />
      <Route path="/imports" element={<ImportWizard />} />
      <Route path="/documents" element={<DocumentLibraryPage />} />
      <Route path="/documents/:documentId" element={<DocumentDetailPage />} />
      <Route path="/tasks" element={<TaskWorkspace />} />
      <Route path="/tasks/folder-events" element={<FolderReviewInbox />} />
      <Route path="/tasks/folder-events/:eventId" element={<FolderReviewInbox />} />
      <Route path="/search" element={<SearchPage />} />
      <Route path="/dashboards" element={<DashboardPage />} />
      <Route path="/audit" element={<AuditTimeline />} />
      {navigationItems
        .slice(1)
        .filter(
          (item) =>
            ![
              "/records",
              "/projects",
              "/imports",
              "/documents",
              "/search",
              "/dashboards",
              "/audit",
              "/tasks"
            ].includes(item.path)
        )
        .map((item) => (
          <Route
            key={item.path}
            path={item.path}
            element={
              item.path === "/admin" ? <ConfigWorkspace /> : <PlaceholderPage item={item} />
            }
          />
        ))}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
