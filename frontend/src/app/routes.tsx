import {
  BarChart3,
  ClipboardCheck,
  Database,
  FileText,
  FolderKanban,
  History,
  Home,
  Plus,
  Search,
  Settings,
  UploadCloud
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import type { LucideIcon } from "lucide-react";
import { useMemo } from "react";
import { Link, Navigate, Route, Routes, useParams } from "react-router-dom";

import { DataTable } from "../components/DataTable";
import { StatusBadge } from "../components/StatusBadge";
import type { StatusTone } from "../components/StatusBadge";
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

type ApiListResponse<T> = T[] | { results?: T[] };

type HomeRecord = {
  id: string | number;
  code?: string;
  title?: string;
  name?: string;
  object_type_key?: string;
  object_type_label?: string;
  owner?: string;
  status?: string;
  updated_at?: string;
  created_at?: string;
};

type HomeTask = {
  id: string | number;
  title?: string;
  state?: string;
  status?: string;
  due_at?: string;
  due_date?: string;
};

type HomeDocument = {
  id: string | number;
  title?: string;
  state?: string;
  status?: string;
};

function HomePage() {
  const recordsQuery = useQuery({
    queryKey: ["home", "records"],
    queryFn: () => apiGet<ApiListResponse<HomeRecord>>("/records/")
  });
  const tasksQuery = useQuery({
    queryKey: ["home", "workflow-tasks", "open"],
    queryFn: () => apiGet<ApiListResponse<HomeTask>>("/workflow-tasks/?state=open")
  });
  const documentsQuery = useQuery({
    queryKey: ["home", "documents"],
    queryFn: () => apiGet<ApiListResponse<HomeDocument>>("/documents/")
  });

  const records = itemsFromResponse(recordsQuery.data);
  const tasks = itemsFromResponse(tasksQuery.data);
  const documents = itemsFromResponse(documentsQuery.data);
  const openRecords = records.filter((record) => record.status !== "archived");
  const overdueTasks = tasks.filter(isOpenTaskOverdue);
  const recentRecords = useMemo(
    () => [...records].sort(compareRecordUpdatedAt).slice(0, 5),
    [records]
  );
  const hasError = recordsQuery.isError || tasksQuery.isError || documentsQuery.isError;

  return (
    <div className="page-stack">
      <section className="workspace-header" aria-labelledby="overview-title">
        <div>
          <p className="section-kicker">Plastic Engineering Data Hub</p>
          <h1 id="overview-title">Operational Overview</h1>
        </div>
        <div className="header-actions">
          <Link className="button button-primary" to="/records/new">
            <Plus aria-hidden="true" size={16} />
            New Record
          </Link>
        </div>
      </section>

      <section className="metrics-grid" aria-label="Workspace metrics">
        <Metric
          label="Open records"
          value={recordsQuery.isLoading ? "Loading" : openRecords.length}
          status="active"
          to="/records"
        />
        <Metric
          label="Pending review"
          value={tasksQuery.isLoading ? "Loading" : tasks.length}
          status="review"
          to="/tasks"
        />
        <Metric
          label="Overdue work"
          value={tasksQuery.isLoading ? "Loading" : overdueTasks.length}
          status="blocked"
          to="/tasks?due=overdue"
        />
        <Metric
          label="Controlled documents"
          value={documentsQuery.isLoading ? "Loading" : documents.length}
          status="ready"
          to="/documents"
        />
      </section>

      {hasError && (
        <div className="admin-alert" role="alert">
          <strong>Operational overview failed</strong>
          <span>{homeErrorMessage(recordsQuery.error ?? tasksQuery.error ?? documentsQuery.error)}</span>
        </div>
      )}

      <section className="table-panel" aria-labelledby="queue-title">
        <div className="panel-heading">
          <div>
            <p className="section-kicker">Queue</p>
            <h2 id="queue-title">Recent Record Activity</h2>
          </div>
          <StatusBadge tone={recordsQuery.isLoading ? "neutral" : recentRecords.length ? "active" : "ready"}>
            {recordsQuery.isLoading ? "Loading" : `${recentRecords.length} Recent`}
          </StatusBadge>
        </div>
        <DataTable
          data={recentRecords}
          emptyMessage={
            recordsQuery.isLoading ? "Loading recent records." : "No record activity is available yet."
          }
          columns={[
            {
              accessorKey: "id",
              header: "Record",
              cell: ({ row }) => (
                <Link className="text-link" to={`/records/${row.original.id}`}>
                  {recordCode(row.original)}
                </Link>
              )
            },
            {
              id: "title",
              header: "Title",
              cell: ({ row }) => recordTitle(row.original)
            },
            {
              accessorKey: "owner",
              header: "Owner",
              cell: ({ row }) => row.original.owner || "Unassigned"
            },
            {
              accessorKey: "status",
              header: "Status",
              cell: ({ getValue }) => (
                <StatusBadge tone={recordStatusTone(getValue<string>())}>
                  {humanizeStatus(getValue<string>() ?? "draft")}
                </StatusBadge>
              )
            },
            {
              accessorKey: "updated",
              header: "Updated",
              cell: ({ row }) => formatDate(row.original.updated_at ?? row.original.created_at)
            }
          ]}
        />
      </section>
    </div>
  );
}

function Metric({
  label,
  to,
  value,
  status
}: {
  label: string;
  to: string;
  value: number | string;
  status: "active" | "ready" | "review" | "blocked";
}) {
  return (
    <Link className="metric metric-link" to={to}>
      <span>{label}</span>
      <strong>{value}</strong>
      <StatusBadge tone={status}>{statusLabelForMetric(status)}</StatusBadge>
    </Link>
  );
}

function statusLabelForMetric(status: "active" | "ready" | "review" | "blocked") {
  const labels = {
    active: "Active",
    ready: "Ready",
    review: "Review",
    blocked: "Blocked"
  };

  return labels[status];
}

function itemsFromResponse<T>(response?: ApiListResponse<T>) {
  if (Array.isArray(response)) {
    return response;
  }

  return response?.results ?? [];
}

function compareRecordUpdatedAt(left: HomeRecord, right: HomeRecord) {
  return recordTimestamp(right) - recordTimestamp(left);
}

function recordTimestamp(record: HomeRecord) {
  const value = record.updated_at ?? record.created_at ?? "";
  const timestamp = Date.parse(value);
  return Number.isNaN(timestamp) ? 0 : timestamp;
}

function recordCode(record: HomeRecord) {
  return record.code ?? String(record.id);
}

function recordTitle(record: HomeRecord) {
  return record.title ?? record.name ?? record.object_type_label ?? record.object_type_key ?? "Untitled record";
}

function recordStatusTone(status?: string): StatusTone {
  if (status === "released") {
    return "ready";
  }

  if (status === "archived") {
    return "neutral";
  }

  return "review";
}

function humanizeStatus(value: string) {
  return value.replace(/[_-]+/g, " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

function formatDate(value?: string) {
  if (!value) {
    return "Not recorded";
  }

  return new Intl.DateTimeFormat("en", { dateStyle: "medium" }).format(new Date(value));
}

function isOpenTaskOverdue(task: HomeTask) {
  const dueDate = task.due_at ?? task.due_date;
  if (!dueDate) {
    return false;
  }

  const timestamp = Date.parse(dueDate);
  return !Number.isNaN(timestamp) && timestamp < Date.now();
}

function homeErrorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Live operational data could not be loaded.";
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
