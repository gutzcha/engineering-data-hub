/*
 * ===
 * File Summary
 * Path: frontend\src\features\dashboards\DashboardPage.tsx
 * Type: typescript
 * Purpose: Frontend feature module implementing business flows and UI surfaces.
 * Primary responsibilities:
 * - Domain behavior is summarized for fast onboarding and avoids full-file reread.
 * - Core symbols: DashboardPage
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
import {
  BarChart3,
  Clock3,
  Loader2,
  RefreshCw,
  SlidersHorizontal
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { DataTable } from "../../components/DataTable";
import { StatusBadge } from "../../components/StatusBadge";
import { apiGet, apiPost } from "../../lib/api";
import { buildSearchPageUrl } from "../search/searchUrl";
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

type DashboardWidgetWidth = "normal" | "wide" | "full";

type DashboardWidgetLayout = {
  hidden?: boolean;
  order?: number;
  width?: DashboardWidgetWidth;
};

type DashboardWidgetLayoutMap = Record<string, DashboardWidgetLayout>;

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
  const [isEditingLayout, setIsEditingLayout] = useState(false);
  const [dashboardLayout, setDashboardLayout] = useState<DashboardWidgetLayoutMap>({});
  const [draggedWidgetId, setDraggedWidgetId] = useState<string | null>(null);
  const [layoutMessage, setLayoutMessage] = useState("");

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
  const orderedWidgets = useMemo(
    () => orderDashboardWidgets(dashboard?.widgets ?? [], dashboardLayout),
    [dashboard?.widgets, dashboardLayout]
  );
  const visibleWidgets = orderedWidgets.filter((widget) => !dashboardLayout[String(widget.id)]?.hidden);
  const hiddenWidgets = orderedWidgets.filter((widget) => dashboardLayout[String(widget.id)]?.hidden);
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

  useEffect(() => {
    if (dashboard) {
      setDashboardLayout(loadDashboardLayout(dashboard.id));
      setLayoutMessage("");
      setDraggedWidgetId(null);
    }
  }, [dashboard]);

  const currentError =
    configQuery.error ??
    savedViewsQuery.error ??
    dashboardQuery.error ??
    runSavedView.error ??
    createSavedView.error;

  function updateWidgetLayout(widgetId: string | number, updater: (layout: DashboardWidgetLayout) => DashboardWidgetLayout) {
    const key = String(widgetId);
    setDashboardLayout((current) => ({
      ...current,
      [key]: updater(current[key] ?? {})
    }));
    setLayoutMessage("Unsaved dashboard layout changes.");
  }

  function dropWidget(targetWidgetId: string | number) {
    if (!dashboard || !draggedWidgetId || draggedWidgetId === String(targetWidgetId)) {
      return;
    }
    const reorderedIds = reorderWidgetIds(orderedWidgets, draggedWidgetId, String(targetWidgetId));
    setDashboardLayout((current) => withWidgetOrder(current, reorderedIds));
    setDraggedWidgetId(null);
    setLayoutMessage("Unsaved dashboard layout changes.");
  }

  function saveDashboardLayout() {
    if (!dashboard) {
      return;
    }
    saveDashboardLayoutToStorage(dashboard.id, dashboardLayout);
    setIsEditingLayout(false);
    setLayoutMessage("Dashboard view saved in this browser.");
  }

  function resetDashboardLayout() {
    if (!dashboard) {
      return;
    }
    clearDashboardLayout(dashboard.id);
    setDashboardLayout({});
    setLayoutMessage("Dashboard layout reset.");
  }

  return (
    <div className="page-stack dashboard-page">
      <section className="workspace-header" aria-labelledby="dashboard-title">
        <div>
          <p className="section-kicker">Operational reporting</p>
          <h1 id="dashboard-title">
            {dashboardQuery.isLoading && dashboardId ? "Loading Dashboard" : dashboard?.name ?? "Dashboards"}
          </h1>
        </div>
        <div className="header-actions">
          <StatusBadge tone={dashboard ? "active" : "neutral"}>
            {dashboard ? `${visibleWidgets.length}/${dashboard.widgets.length} Widgets` : "Choose Dashboard"}
          </StatusBadge>
          {dashboard && (
            <>
              <button
                className="button button-secondary"
                type="button"
                onClick={() => setIsEditingLayout((current) => !current)}
              >
                <SlidersHorizontal aria-hidden="true" size={16} />
                {isEditingLayout ? "Close Designer" : "Design Dashboard"}
              </button>
              <button className="button button-primary" type="button" onClick={saveDashboardLayout}>
                Save View
              </button>
            </>
          )}
        </div>
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
            <span>Configured Dashboard</span>
            <select
              aria-label="Configured dashboard"
              value={dashboardId}
              onChange={(event) => setDashboardId(event.target.value)}
            >
              <option value="">Choose dashboard</option>
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
              {layoutMessage && <p className="admin-muted">{layoutMessage}</p>}
              {isEditingLayout && (
                <div className="dashboard-layout-toolbar" aria-label="Dashboard designer controls">
                  <button className="button button-secondary" type="button" onClick={resetDashboardLayout}>
                    Reset Layout
                  </button>
                  <span>Drag widgets to reorder. Use size buttons to resize, hide, or restore widgets.</span>
                </div>
              )}
            </div>
          </section>

          {isEditingLayout && hiddenWidgets.length > 0 && (
            <section className="table-panel dashboard-palette" aria-labelledby="hidden-widget-title">
              <div className="panel-heading">
                <div>
                  <p className="section-kicker">Widget options</p>
                  <h2 id="hidden-widget-title">Hidden Widgets</h2>
                </div>
                <StatusBadge tone="neutral">{hiddenWidgets.length} Hidden</StatusBadge>
              </div>
              <div className="dashboard-palette-list">
                {hiddenWidgets.map((widget) => (
                  <button
                    className="button button-secondary"
                    type="button"
                    key={widget.id}
                    onClick={() => updateWidgetLayout(widget.id, (layout) => ({ ...layout, hidden: false }))}
                  >
                    Add {widget.title}
                  </button>
                ))}
              </div>
            </section>
          )}

          <div className={isEditingLayout ? "dashboard-widget-grid dashboard-widget-grid-editing" : "dashboard-widget-grid"}>
            {visibleWidgets.map((widget) => (
              <DashboardWidgetPanel
                widget={widget}
                key={widget.id}
                isEditingLayout={isEditingLayout}
                layout={dashboardLayout[String(widget.id)]}
                onDragStart={() => setDraggedWidgetId(String(widget.id))}
                onDrop={() => dropWidget(widget.id)}
                onResize={(width) => updateWidgetLayout(widget.id, (layout) => ({ ...layout, width }))}
                onHide={() => updateWidgetLayout(widget.id, (layout) => ({ ...layout, hidden: true }))}
              />
            ))}
          </div>
        </>
      ) : (
        <section className="empty-state">
          <BarChart3 aria-hidden="true" size={28} />
          <div>
            <h2>{dashboardQuery.isLoading ? "Loading dashboard" : "No dashboard loaded"}</h2>
            <p>Choose a configured dashboard to load its published widget layout.</p>
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

function DashboardWidgetPanel({
  widget,
  isEditingLayout,
  layout,
  onDragStart,
  onDrop,
  onResize,
  onHide
}: {
  widget: DashboardWidget;
  isEditingLayout: boolean;
  layout?: DashboardWidgetLayout;
  onDragStart: () => void;
  onDrop: () => void;
  onResize: (width: DashboardWidgetWidth) => void;
  onHide: () => void;
}) {
  const items = widget.data?.items ?? [];
  const width = layout?.width ?? "normal";

  return (
    <section
      className={`table-panel dashboard-widget dashboard-widget-${width}`}
      aria-labelledby={`dashboard-widget-${widget.id}`}
      draggable={isEditingLayout}
      onDragStart={onDragStart}
      onDragOver={(event) => {
        if (isEditingLayout) {
          event.preventDefault();
        }
      }}
      onDrop={(event) => {
        event.preventDefault();
        onDrop();
      }}
    >
      <div className="panel-heading">
        <div>
          <p className="section-kicker">{humanize(widget.widget_type)}</p>
          <h2 id={`dashboard-widget-${widget.id}`}>{widget.title}</h2>
        </div>
        {isEditingLayout ? (
          <div className="widget-layout-actions">
            <button className="button button-secondary button-compact" type="button" onClick={() => onResize("normal")}>
              1x
            </button>
            <button className="button button-secondary button-compact" type="button" onClick={() => onResize("wide")}>
              2x
            </button>
            <button className="button button-secondary button-compact" type="button" onClick={() => onResize("full")}>
              Full
            </button>
            <button className="button button-secondary button-compact" type="button" onClick={onHide}>
              Hide
            </button>
          </div>
        ) : (
          <StatusBadge tone={items.length ? "active" : "neutral"}>{items.length} Items</StatusBadge>
        )}
      </div>
      <div className="record-panel-body dashboard-widget-body">
        {items.length === 0 ? (
          <p className="admin-muted">No widget data returned.</p>
        ) : (
          items.map((item, index) => (
            <WidgetItem item={item} key={String(item.id ?? item.key ?? index)} widgetType={widget.widget_type} />
          ))
        )}
      </div>
    </section>
  );
}

function WidgetItem({ item, widgetType }: { item: DashboardWidgetItem; widgetType: string }) {
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
  const href = recordHref(item, widgetType);

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

function recordHref(item: DashboardWidgetItem, widgetType?: string) {
  if (typeof item.href === "string" && item.href.startsWith("/")) {
    return item.href;
  }
  if (typeof item.path === "string" && item.path.startsWith("/")) {
    return item.path;
  }
  if (item.record_id) {
    return `/records/${String(item.record_id)}`;
  }
  if (item.object_type === "record" && item.object_id) {
    return `/records/${String(item.object_id)}`;
  }
  if (item.project_id) {
    return `/projects/${String(item.project_id)}`;
  }
  if (item.object_type === "project" && item.object_id) {
    return `/projects/${String(item.object_id)}`;
  }
  if (item.document_id) {
    return `/documents/${String(item.document_id)}`;
  }
  if (item.object_type === "document" && item.object_id) {
    return `/documents/${String(item.object_id)}`;
  }

  const structuredHref = structuredDashboardSearchHref(item, widgetType);
  if (structuredHref) {
    return structuredHref;
  }

  if (item.search_fallback === false) {
    return undefined;
  }

  const q = [item.code, item.title, item.name, item.key, item.action, item.object_type_key, item.object_type]
    .filter(Boolean)
    .map(String)
    .join(" ");
  return buildSearchPageUrl({
    type: item.object_type === "project" ? "projects" : item.object_type === "document" ? "documents" : "records",
    q,
    status: typeof item.status === "string" ? item.status : undefined,
    object_type_key: typeof item.object_type_key === "string" ? item.object_type_key : undefined
  });
}

function structuredDashboardSearchHref(item: DashboardWidgetItem, widgetType?: string) {
  if (widgetType === "count_by_status") {
    const status = stringValue(item.status) ?? stringValue(item.key) ?? stringValue(item.name) ?? stringValue(item.title);
    return status ? buildSearchPageUrl({ type: "records", status }) : undefined;
  }

  if (widgetType === "count_by_object_type") {
    const objectTypeKey =
      stringValue(item.object_type_key) ??
      stringValue(item.key) ??
      stringValue(item.object_type) ??
      stringValue(item.name) ??
      stringValue(item.title);
    return objectTypeKey ? buildSearchPageUrl({ type: "records", object_type_key: objectTypeKey }) : undefined;
  }

  if (item.count !== undefined && typeof item.status === "string") {
    return buildSearchPageUrl({ type: "records", status: item.status });
  }

  if (item.count !== undefined && typeof item.object_type_key === "string") {
    return buildSearchPageUrl({ type: "records", object_type_key: item.object_type_key });
  }

  return undefined;
}

function stringValue(value: unknown) {
  if (value === null || value === undefined || value === "") {
    return undefined;
  }
  return String(value);
}

function widgetSubtitle(item: DashboardWidgetItem) {
  if (item.subtitle) {
    return String(item.subtitle);
  }
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

function orderDashboardWidgets(widgets: DashboardWidget[], layout: DashboardWidgetLayoutMap) {
  return [...widgets].sort((first, second) => {
    const firstOrder = layout[String(first.id)]?.order ?? first.sort_order ?? widgets.indexOf(first);
    const secondOrder = layout[String(second.id)]?.order ?? second.sort_order ?? widgets.indexOf(second);
    return firstOrder - secondOrder;
  });
}

function reorderWidgetIds(widgets: DashboardWidget[], sourceId: string, targetId: string) {
  const ids = widgets.map((widget) => String(widget.id));
  const sourceIndex = ids.indexOf(sourceId);
  const targetIndex = ids.indexOf(targetId);
  if (sourceIndex === -1 || targetIndex === -1) {
    return ids;
  }
  const [source] = ids.splice(sourceIndex, 1);
  ids.splice(targetIndex, 0, source);
  return ids;
}

function withWidgetOrder(layout: DashboardWidgetLayoutMap, widgetIds: string[]) {
  return widgetIds.reduce<DashboardWidgetLayoutMap>(
    (next, widgetId, index) => ({
      ...next,
      [widgetId]: {
        ...(layout[widgetId] ?? {}),
        order: index
      }
    }),
    { ...layout }
  );
}

function dashboardLayoutKey(dashboardId: string | number) {
  return `plastic-data-hub-dashboard-layout:${dashboardId}`;
}

function loadDashboardLayout(dashboardId: string | number): DashboardWidgetLayoutMap {
  try {
    return JSON.parse(window.localStorage.getItem(dashboardLayoutKey(dashboardId)) ?? "{}") as DashboardWidgetLayoutMap;
  } catch {
    return {};
  }
}

function saveDashboardLayoutToStorage(dashboardId: string | number, layout: DashboardWidgetLayoutMap) {
  window.localStorage.setItem(dashboardLayoutKey(dashboardId), JSON.stringify(layout));
}

function clearDashboardLayout(dashboardId: string | number) {
  window.localStorage.removeItem(dashboardLayoutKey(dashboardId));
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

