import {
  BarChart3,
  ClipboardCheck,
  Database,
  Download,
  FileText,
  FolderKanban,
  Home,
  Plus,
  Search,
  Settings,
  SlidersHorizontal
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { Navigate, Route, Routes, useParams } from "react-router-dom";

import { DataTable } from "../components/DataTable";
import { StatusBadge } from "../components/StatusBadge";
import { ConfigWorkspace } from "../features/admin-config/ConfigWorkspace";
import {
  DocumentDetailPage,
  DocumentLibraryPage
} from "../features/documents/DocumentPanel";
import { ProjectDetail } from "../features/projects/ProjectDetail";
import { ProjectList } from "../features/projects/ProjectList";
import { RecordDetail } from "../features/records/RecordDetail";
import { RecordList } from "../features/records/RecordList";
import { SearchPage } from "../features/search/SearchPage";
import { TaskInbox } from "../features/workflows/TaskInbox";

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

type RecordQueueItem = {
  id: string;
  area: string;
  owner: string;
  status: "ready" | "review" | "blocked";
  updated: string;
};

const recordQueue: RecordQueueItem[] = [
  {
    id: "PE-1042",
    area: "Injection molding trials",
    owner: "Materials Lab",
    status: "review",
    updated: "Today"
  },
  {
    id: "PE-1038",
    area: "Regrind characterization",
    owner: "Process Engineering",
    status: "ready",
    updated: "Yesterday"
  },
  {
    id: "PE-1029",
    area: "Supplier resin dossier",
    owner: "Quality",
    status: "blocked",
    updated: "Jun 4"
  }
];

const statusLabel: Record<RecordQueueItem["status"], string> = {
  ready: "Ready",
  review: "In Review",
  blocked: "Blocked"
};

function HomePage() {
  return (
    <div className="page-stack">
      <section className="workspace-header" aria-labelledby="overview-title">
        <div>
          <p className="section-kicker">Plastic Engineering Data Hub</p>
          <h1 id="overview-title">Operational Overview</h1>
        </div>
        <div className="header-actions">
          <button className="button button-secondary" type="button">
            <Download aria-hidden="true" size={16} />
            Export
          </button>
          <button className="button button-primary" type="button">
            <Plus aria-hidden="true" size={16} />
            New Record
          </button>
        </div>
      </section>

      <section className="metrics-grid" aria-label="Workspace metrics">
        <Metric label="Open records" value="128" status="active" />
        <Metric label="Pending review" value="17" status="review" />
        <Metric label="Blocked tasks" value="4" status="blocked" />
        <Metric label="Controlled documents" value="312" status="ready" />
      </section>

      <section className="table-panel" aria-labelledby="queue-title">
        <div className="panel-heading">
          <div>
            <p className="section-kicker">Queue</p>
            <h2 id="queue-title">Recent Record Activity</h2>
          </div>
          <StatusBadge tone="review">Review Needed</StatusBadge>
        </div>
        <DataTable
          data={recordQueue}
          columns={[
            {
              accessorKey: "id",
              header: "Record"
            },
            {
              accessorKey: "area",
              header: "Area"
            },
            {
              accessorKey: "owner",
              header: "Owner"
            },
            {
              accessorKey: "status",
              header: "Status",
              cell: ({ getValue }) => (
                <StatusBadge tone={getValue<RecordQueueItem["status"]>()}>
                  {statusLabel[getValue<RecordQueueItem["status"]>()]}
                </StatusBadge>
              )
            },
            {
              accessorKey: "updated",
              header: "Updated"
            }
          ]}
        />
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
  status: "active" | "ready" | "review" | "blocked";
}) {
  return (
    <article className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
      <StatusBadge tone={status}>{statusLabelForMetric(status)}</StatusBadge>
    </article>
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

function PlaceholderPage({ item }: { item: NavigationItem }) {
  const Icon = item.icon;

  return (
    <div className="page-stack">
      <section className="workspace-header" aria-labelledby={`${item.label}-title`}>
        <div>
          <p className="section-kicker">{item.description}</p>
          <h1 id={`${item.label}-title`}>{item.label}</h1>
        </div>
        <button className="button button-secondary" type="button">
          <SlidersHorizontal aria-hidden="true" size={16} />
          Configure View
        </button>
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

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/records" element={<RecordList />} />
      <Route path="/records/:recordId" element={<RecordDetail />} />
      <Route path="/projects" element={<ProjectList />} />
      <Route path="/projects/:projectId" element={<ProjectDetail />} />
      <Route path="/documents" element={<DocumentLibraryPage />} />
      <Route path="/documents/:documentId" element={<DocumentDetailPage />} />
      <Route path="/tasks" element={<TaskInbox />} />
      <Route
        path="/tasks/folder-events/:eventId"
        element={
          <SearchTargetPlaceholder
            description="Folder review event search target"
            idParam="eventId"
            label="Folder Event"
          />
        }
      />
      <Route path="/search" element={<SearchPage />} />
      {navigationItems
        .slice(1)
        .filter((item) => !["/records", "/projects", "/documents", "/search", "/tasks"].includes(item.path))
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
