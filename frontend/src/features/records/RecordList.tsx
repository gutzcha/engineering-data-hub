import { useQuery } from "@tanstack/react-query";
import { Filter, Plus, Search } from "lucide-react";
import type { FormEvent } from "react";
import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { DataTable } from "../../components/DataTable";
import { StatusBadge } from "../../components/StatusBadge";
import { apiGet } from "../../lib/api";
import { ConfigData } from "./DynamicRecordForm";

type ConfigVersion = {
  data?: ConfigData & {
    saved_views?: SavedView[];
    dashboards?: DashboardLink[];
  };
};

type RecordListItem = {
  id: string | number;
  code?: string;
  title?: string;
  name?: string;
  object_type_key?: string;
  object_type_label?: string;
  status?: string;
  owner?: string;
  updated_at?: string;
};

type SavedView = {
  id?: string | number;
  key?: string;
  label?: string;
  name?: string;
  filters?: Record<string, string>;
};

type DashboardLink = {
  id?: string | number;
  key?: string;
  label?: string;
  name?: string;
  filters?: Record<string, string>;
};

export function RecordList() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [searchText, setSearchText] = useState(searchParams.get("q") ?? "");
  const objectTypeFilter = searchParams.get("object_type_key") ?? "";
  const statusFilter = searchParams.get("status") ?? "";
  const savedViewFilter = searchParams.get("saved_view") ?? "";
  const dashboardFilter = searchParams.get("dashboard") ?? "";

  const configQuery = useQuery({
    queryKey: ["config", "active"],
    queryFn: () => apiGet<ConfigVersion>("/config/active/")
  });

  const recordsQuery = useQuery({
    queryKey: ["records", objectTypeFilter, statusFilter, searchParams.get("q"), savedViewFilter, dashboardFilter],
    queryFn: () => apiGet<RecordListItem[]>(`/records/${recordsQueryString(searchParams)}`)
  });

  const objectTypes = configQuery.data?.data?.object_types ?? [];
  const savedViews = configQuery.data?.data?.saved_views ?? [];
  const dashboards = configQuery.data?.data?.dashboards ?? [];
  const records = useMemo(
    () => filterRecords(recordsQuery.data ?? [], searchParams.get("q") ?? ""),
    [recordsQuery.data, searchParams]
  );

  function updateFilter(key: string, value: string) {
    const next = new URLSearchParams(searchParams);
    if (value) {
      next.set(key, value);
    } else {
      next.delete(key);
    }
    setSearchParams(next);
  }

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    updateFilter("q", searchText.trim());
  }

  return (
    <div className="page-stack">
      <section className="workspace-header" aria-labelledby="records-title">
        <div>
          <p className="section-kicker">Material, trial, and test records</p>
          <h1 id="records-title">Records</h1>
        </div>
        <div className="header-actions">
          <Link className="button button-primary" to="/records/new">
            <Plus aria-hidden="true" size={16} />
            New Record
          </Link>
        </div>
      </section>

      <section className="filter-panel" aria-label="Record filters">
        <form className="search-form" onSubmit={submitSearch}>
          <label className="field-control">
            <span>Search</span>
            <input
              aria-label="Search records"
              value={searchText}
              onChange={(event) => setSearchText(event.target.value)}
            />
          </label>
          <button className="button button-secondary" type="submit">
            <Search aria-hidden="true" size={16} />
            Search
          </button>
        </form>
        <div className="filter-grid">
          <FilterSelect
            label="Object type"
            value={objectTypeFilter}
            options={objectTypes.map((objectType) => ({
              value: objectType.key,
              label: objectType.plural_label ?? objectType.label ?? objectType.key
            }))}
            onChange={(value) => updateFilter("object_type_key", value)}
          />
          <FilterSelect
            label="Status"
            value={statusFilter}
            options={["draft", "released", "archived"].map((status) => ({
              value: status,
              label: humanize(status)
            }))}
            onChange={(value) => updateFilter("status", value)}
          />
          <FilterSelect
            label="Saved view"
            value={savedViewFilter}
            options={savedViews.map((view) => ({
              value: String(view.key ?? view.id),
              label: view.label ?? view.name ?? String(view.key ?? view.id)
            }))}
            onChange={(value) => updateFilter("saved_view", value)}
          />
          <FilterSelect
            label="Dashboard link"
            value={dashboardFilter}
            options={dashboards.map((dashboard) => ({
              value: String(dashboard.key ?? dashboard.id),
              label: dashboard.label ?? dashboard.name ?? String(dashboard.key ?? dashboard.id)
            }))}
            onChange={(value) => updateFilter("dashboard", value)}
          />
        </div>
        <div className="active-filter-row" aria-label="Active record filters">
          {[objectTypeFilter, statusFilter, savedViewFilter, dashboardFilter].filter(Boolean).length === 0 ? (
            <span>No saved view or dashboard filters applied.</span>
          ) : (
            <>
              {objectTypeFilter && <StatusBadge tone="active">Type: {objectTypeFilter}</StatusBadge>}
              {statusFilter && <StatusBadge tone="review">Status: {statusFilter}</StatusBadge>}
              {savedViewFilter && <StatusBadge tone="ready">View: {savedViewFilter}</StatusBadge>}
              {dashboardFilter && <StatusBadge tone="active">Dashboard: {dashboardFilter}</StatusBadge>}
            </>
          )}
        </div>
      </section>

      <section className="table-panel" aria-labelledby="record-list-title">
        <div className="panel-heading">
          <div>
            <p className="section-kicker">Record queue</p>
            <h2 id="record-list-title">Published Record Set</h2>
          </div>
          <StatusBadge tone={recordsQuery.isLoading ? "neutral" : "active"}>
            {recordsQuery.isLoading ? "Loading" : `${records.length} Records`}
          </StatusBadge>
        </div>
        <DataTable
          data={records}
          emptyMessage="No records match the selected filters."
          columns={[
            {
              accessorKey: "code",
              header: "Record",
              cell: ({ row }) => (
                <Link className="text-link" to={`/records/${row.original.id}`}>
                  {row.original.code ?? row.original.id}
                </Link>
              )
            },
            {
              accessorKey: "title",
              header: "Title",
              cell: ({ row }) => row.original.title ?? row.original.name ?? "Untitled"
            },
            {
              accessorKey: "object_type_label",
              header: "Type",
              cell: ({ row }) => row.original.object_type_label ?? row.original.object_type_key ?? "Record"
            },
            {
              accessorKey: "status",
              header: "Status",
              cell: ({ row }) => (
                <StatusBadge tone={statusTone(row.original.status)}>
                  {row.original.status ?? "unknown"}
                </StatusBadge>
              )
            },
            {
              accessorKey: "updated_at",
              header: "Updated",
              cell: ({ row }) => formatDateTime(row.original.updated_at)
            }
          ]}
        />
      </section>
      {recordsQuery.error && (
        <div className="admin-alert" role="alert">
          <strong>Record list failed</strong>
          <span>{errorMessage(recordsQuery.error)}</span>
        </div>
      )}
    </div>
  );
}

function FilterSelect({
  label,
  value,
  options,
  onChange
}: {
  label: string;
  value: string;
  options: Array<{ value: string; label: string }>;
  onChange: (value: string) => void;
}) {
  return (
    <label className="field-control">
      <span>{label}</span>
      <select aria-label={label} value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="">All</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function recordsQueryString(searchParams: URLSearchParams) {
  const params = new URLSearchParams();

  ["object_type_key", "status", "q", "saved_view", "dashboard"].forEach((key) => {
    const value = searchParams.get(key);
    if (value) {
      params.set(key, value);
    }
  });

  const query = params.toString();
  return query ? `?${query}` : "";
}

function filterRecords(records: RecordListItem[], search: string) {
  const query = search.trim().toLowerCase();

  if (!query) {
    return records;
  }

  return records.filter((record) =>
    [record.code, record.title, record.name, record.object_type_label, record.object_type_key]
      .filter(Boolean)
      .some((value) => String(value).toLowerCase().includes(query))
  );
}

function statusTone(status?: string) {
  if (status === "released" || status === "ready") {
    return "ready";
  }

  if (status === "blocked") {
    return "blocked";
  }

  if (status === "review" || status === "draft") {
    return "review";
  }

  return "neutral";
}

function formatDateTime(value?: string) {
  if (!value) {
    return "Not recorded";
  }

  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}

function humanize(value: string) {
  return value.replace(/[_-]+/g, " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Record list request failed.";
}
