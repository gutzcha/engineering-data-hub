import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BarChart3,
  Clock3,
  Loader2,
  RefreshCw,
  Search,
  SlidersHorizontal
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { DataTable } from "../../components/DataTable";
import { StatusBadge } from "../../components/StatusBadge";
import { apiGet, apiPost } from "../../lib/api";
import {
  DashboardObjectType,
  SavedView,
  SavedViewBuilder,
  SavedViewDraft
} from "./SavedViewBuilder";

type ConfigVersion = {
  data?: {
    object_types?: DashboardObjectType[];
    dashboards?: DashboardLink[];
  };
};

type DashboardLink = {
  id?: string | number;
  key?: string | number;
  name?: string;
  label?: string;
};

type Dashboard = {
  id: string | number;
  name: string;
  description?: string;
  config?: Record<string, unknown>;
  widgets: DashboardWidget[];
};

type DashboardWidget = {
  id: string | number;
  title: string;
  widget_type: string;
  config?: Record<string, unknown>;
  sort_order?: number;
  data?: {
    items?: DashboardWidgetItem[];
  };
};

type DashboardWidgetItem = Record<string, unknown>;

type SavedViewListResponse = {
  results?: SavedView[];
};

type SavedViewResults = {
  count?: number;
  results?: SavedViewResultRow[];
};

type SavedViewResultRow = Record<string, unknown> & {
  id?: string | number;
};

export function DashboardPage() {
  const queryClient = useQueryClient();
  const [dashboardId, setDashboardId] = useState("");
  const [selectedSavedViewId, setSelectedSavedViewId] = useState("");
  const [savedViewResults, setSavedViewResults] = useState<SavedViewResults | null>(null);

  const configQuery = useQuery({
    queryKey: ["config", "active"],
    queryFn: () => apiGet<ConfigVersion>("/config/active/")
  });

  const savedViewsQuery = useQuery({
    queryKey: ["saved-views"],
    queryFn: () => apiGet<SavedViewListResponse>("/saved-views/")
  });

  const dashboardQuery = useQuery({
    queryKey: ["dashboards", dashboardId],
    queryFn: () => apiGet<Dashboard>(`/dashboards/${dashboardId}/`),
    enabled: Boolean(dashboardId.trim())
  });

  const runSavedView = useMutation({
    mutationFn: (savedViewId: string) =>
      apiGet<SavedViewResults>(`/saved-views/${savedViewId}/results/?limit=50`),
    onSuccess: (result) => {
      setSavedViewResults(result);
    }
  });

  const createSavedView = useMutation({
    mutationFn: (draft: SavedViewDraft) => apiPost<SavedView>("/saved-views/", draft),
    onSuccess: (view) => {
      setSelectedSavedViewId(String(view.id));
      void queryClient.invalidateQueries({ queryKey: ["saved-views"] });
    }
  });

  const dashboardLinks = configQuery.data?.data?.dashboards ?? [];
  const objectTypes = configQuery.data?.data?.object_types ?? [];
  const savedViews = savedViewsQuery.data?.results ?? [];
  const dashboard = dashboardQuery.data;
  const selectedSavedView = savedViews.find((view) => String(view.id) === selectedSavedViewId);
  const resultColumns = useMemo(
    () => columnsForResults(savedViewResults?.results ?? [], selectedSavedView?.columns),
    [savedViewResults?.results, selectedSavedView?.columns]
  );

  useEffect(() => {
    if (!dashboardId && dashboardLinks[0]) {
      setDashboardId(String(dashboardLinks[0].id ?? dashboardLinks[0].key ?? ""));
    }
  }, [dashboardId, dashboardLinks]);

  const currentError =
    configQuery.error ??
    savedViewsQuery.error ??
    dashboardQuery.error ??
    runSavedView.error ??
    createSavedView.error;

  return (
    <div className="page-stack dashboard-page">
      <section className="workspace-header" aria-labelledby="dashboard-title">
        <div>
          <p className="section-kicker">Operational reporting</p>
          <h1 id="dashboard-title">
            {dashboardQuery.isLoading && dashboardId ? "Loading Dashboard" : dashboard?.name ?? "Dashboards"}
          </h1>
        </div>
        <StatusBadge tone={dashboard ? "active" : "neutral"}>
          {dashboard ? `${dashboard.widgets.length} Widgets` : "No Dashboard Selected"}
        </StatusBadge>
      </section>

      {currentError && (
        <div className="admin-alert" role="alert">
          <strong>Dashboard request failed</strong>
          <span>{errorMessage(currentError)}</span>
        </div>
      )}

      <section className="filter-panel" aria-label="Dashboard controls">
        <div className="dashboard-controls">
          <label className="field-control">
            <span>Dashboard ID</span>
            <input
              aria-label="Dashboard id"
              value={dashboardId}
              onChange={(event) => setDashboardId(event.target.value)}
            />
          </label>
          <label className="field-control">
            <span>Configured Dashboard</span>
            <select
              aria-label="Configured dashboard"
              value={dashboardId}
              onChange={(event) => setDashboardId(event.target.value)}
            >
              <option value="">Manual ID</option>
              {dashboardLinks.map((link) => {
                const value = String(link.id ?? link.key ?? "");
                return (
                  <option value={value} key={value || link.name || link.label}>
                    {link.name ?? link.label ?? value}
                  </option>
                );
              })}
            </select>
          </label>
          <button
            className="button button-secondary"
            type="button"
            onClick={() => void dashboardQuery.refetch()}
            disabled={!dashboardId || dashboardQuery.isFetching}
          >
            {dashboardQuery.isFetching ? (
              <Loader2 aria-hidden="true" size={16} />
            ) : (
              <RefreshCw aria-hidden="true" size={16} />
            )}
            Refresh
          </button>
        </div>
      </section>

      {dashboard ? (
        <>
          <section className="table-panel dashboard-summary" aria-labelledby="dashboard-summary-title">
            <div className="panel-heading">
              <div>
                <p className="section-kicker">Dashboard</p>
                <h2 id="dashboard-summary-title">{dashboard.name}</h2>
              </div>
              <SlidersHorizontal aria-hidden="true" size={18} />
            </div>
            <div className="record-panel-body">
              <p className="admin-muted">{dashboard.description || "No dashboard description recorded."}</p>
            </div>
          </section>

          <div className="dashboard-widget-grid">
            {dashboard.widgets.map((widget) => (
              <DashboardWidgetPanel widget={widget} key={widget.id} />
            ))}
          </div>
        </>
      ) : (
        <section className="empty-state">
          <BarChart3 aria-hidden="true" size={28} />
          <div>
            <h2>{dashboardQuery.isLoading ? "Loading dashboard" : "No dashboard loaded"}</h2>
            <p>Enter a dashboard ID or choose a configured dashboard link.</p>
          </div>
        </section>
      )}

      <SavedViewBuilder
        objectTypes={objectTypes}
        savedViews={savedViews}
        selectedSavedViewId={selectedSavedViewId}
        isRunning={runSavedView.isPending}
        isSaving={createSavedView.isPending}
        onCreate={(draft) => createSavedView.mutate(draft)}
        onRun={() => selectedSavedViewId && runSavedView.mutate(selectedSavedViewId)}
        onSelectSavedView={(savedViewId) => {
          setSelectedSavedViewId(savedViewId);
          setSavedViewResults(null);
        }}
      />

      <section className="table-panel" aria-labelledby="saved-view-results-title">
        <div className="panel-heading">
          <div>
            <p className="section-kicker">List view results</p>
            <h2 id="saved-view-results-title">Saved View Results</h2>
          </div>
          <StatusBadge tone={savedViewResults?.results?.length ? "active" : "neutral"}>
            {savedViewResults ? `${savedViewResults.count ?? savedViewResults.results?.length ?? 0} Rows` : "Not run"}
          </StatusBadge>
        </div>
        <DataTable<SavedViewResultRow>
          data={savedViewResults?.results ?? []}
          emptyMessage={runSavedView.isPending ? "Loading saved view results." : "Run a saved view to load records."}
          columns={resultColumns.map((column) => ({
            id: column,
            header: humanize(column),
            accessorFn: (row: SavedViewResultRow) => valueForColumn(row, column),
            cell: ({ getValue }) => formatCell(getValue())
          }))}
        />
      </section>
    </div>
  );
}

function DashboardWidgetPanel({ widget }: { widget: DashboardWidget }) {
  const items = widget.data?.items ?? [];

  return (
    <section className="table-panel dashboard-widget" aria-labelledby={`dashboard-widget-${widget.id}`}>
      <div className="panel-heading">
        <div>
          <p className="section-kicker">{humanize(widget.widget_type)}</p>
          <h2 id={`dashboard-widget-${widget.id}`}>{widget.title}</h2>
        </div>
        <StatusBadge tone={items.length ? "active" : "neutral"}>{items.length} Items</StatusBadge>
      </div>
      <div className="record-panel-body dashboard-widget-body">
        {items.length === 0 ? (
          <p className="admin-muted">No widget data returned.</p>
        ) : (
          items.map((item, index) => (
            <WidgetItem item={item} key={String(item.id ?? item.key ?? index)} />
          ))
        )}
      </div>
    </section>
  );
}

function WidgetItem({ item }: { item: DashboardWidgetItem }) {
  const title =
    item.title ??
    item.name ??
    item.key ??
    item.action ??
    item.code ??
    item.object_type ??
    item.id ??
    "Item";
  const count = item.count;
  const href = recordHref(item);

  const content = (
    <>
      <span>
        <strong>{String(title)}</strong>
        <small>{widgetSubtitle(item)}</small>
      </span>
      {count !== undefined ? (
        <strong className="widget-count">{String(count)}</strong>
      ) : (
        <Clock3 aria-hidden="true" size={16} />
      )}
    </>
  );

  return href ? (
    <Link className="search-result dashboard-widget-item" to={href}>
      {content}
    </Link>
  ) : (
    <div className="search-result dashboard-widget-item">
      {content}
    </div>
  );
}

function recordHref(item: DashboardWidgetItem) {
  if (item.record_id) {
    return `/records/${String(item.record_id)}`;
  }
  if (item.object_type === "record" && item.object_id) {
    return `/records/${String(item.object_id)}`;
  }
  return undefined;
}

function widgetSubtitle(item: DashboardWidgetItem) {
  return [
    item.object_type_key,
    item.object_type,
    item.object_id,
    item.actor_username,
    item.state,
    item.due_date,
    item.created_at
  ]
    .filter(Boolean)
    .map(String)
    .join(" · ");
}

function columnsForResults(rows: SavedViewResultRow[], configuredColumns?: string[]) {
  if (configuredColumns?.length) {
    return configuredColumns;
  }
  const first = rows[0];
  if (!first) {
    return ["code", "title", "status"];
  }
  return Object.keys(first).filter((key) => key !== "id");
}

function valueForColumn(row: SavedViewResultRow, column: string) {
  if (column in row) {
    return row[column];
  }
  if (column.startsWith("data.") && typeof row.data === "object" && row.data !== null) {
    return (row.data as Record<string, unknown>)[column.slice("data.".length)];
  }
  return "";
}

function formatCell(value: unknown) {
  if (value === null || value === undefined || value === "") {
    return "Not recorded";
  }
  if (Array.isArray(value)) {
    return value.join(", ");
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}

function humanize(value: string) {
  return value.replace(/[._-]+/g, " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Dashboard request failed.";
}
