/*
 * ===
 * File Summary
 * Path: frontend\src\features\projects\ProjectList.tsx
 * Type: typescript
 * Purpose: Live project queue with status and record-based filters.
 * Primary responsibilities:
 * - Core symbols: ProjectList
 * Inputs:
 * - Downstream and upstream interactions in the same domain.
 * Outputs:
 * - API payloads, records, side effects, or UI views.
 * ===
 */

import { useQuery } from "@tanstack/react-query";
import { Filter, Plus, Search, Search as SearchIcon, Workflow } from "lucide-react";
import { FormEvent, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { DataTable } from "../../components/DataTable";
import { StatusBadge } from "../../components/StatusBadge";
import { apiGet } from "../../lib/api";
import { buildSearchPageUrl } from "../search/searchUrl";
import { WorkloadView } from "./WorkloadView";

type ProjectListItem = {
  id: string;
  name?: string;
  status?: string;
  description?: string;
  record?: string;
  record_code?: string;
  created_at?: string;
  updated_at?: string;
};

type PaginatedProjectList = {
  results?: ProjectListItem[];
};

export function ProjectList() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [searchText, setSearchText] = useState(searchParams.get("q") ?? "");
  const statusFilter = searchParams.get("status") ?? "";
  const [directProjectId, setDirectProjectId] = useState("");
  const [directProjectError, setDirectProjectError] = useState("");

  const projectsQuery = useQuery({
    queryKey: ["projects", searchParams.toString()],
    queryFn: () =>
      apiGet<ProjectListItem[] | PaginatedProjectList>(`/projects/${projectsQueryString(searchParams)}`)
  });

  const rawProjects = useMemo(() => asProjectList(projectsQuery.data), [projectsQuery.data]);
  const statusOptions = useMemo(
    () => uniqueSortedOptions(rawProjects, (project) => project.status),
    [rawProjects]
  );

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const next = new URLSearchParams(searchParams);
    if (searchText.trim()) {
      next.set("q", searchText.trim());
    } else {
      next.delete("q");
    }
    setSearchParams(next);
  }

  function updateStatus(value: string) {
    const next = new URLSearchParams(searchParams);
    if (value) {
      next.set("status", value);
    } else {
      next.delete("status");
    }
    setSearchParams(next);
  }

  function openByUuid(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const targetProject = directProjectId.trim();
    if (!targetProject) {
      setDirectProjectError("Enter a project code, name, or UUID.");
      return;
    }

    const matchedProject = rawProjects.find((project) =>
      [project.id, project.record, project.record_code, project.name]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase() === targetProject.toLowerCase())
    );

    setDirectProjectError("");
    if (matchedProject) {
      navigate(`/projects/${matchedProject.id}`);
      return;
    }

    if (isUuid(targetProject)) {
      navigate(`/projects/${targetProject}`);
      return;
    }

    navigate(buildSearchPageUrl({ type: "projects", q: targetProject }));
  }

  return (
    <div className="page-stack project-page">
      <section className="workspace-header" aria-labelledby="projects-title">
        <div>
          <p className="section-kicker">Engineering project workspaces</p>
          <h1 id="projects-title">Projects</h1>
        </div>
        <div className="header-actions">
          <Link
            className="button button-secondary"
            to={buildSearchPageUrl({ type: "projects", q: searchText, status: statusFilter })}
          >
            <Filter aria-hidden="true" size={16} />
            Advanced Search
          </Link>
          <Link className="button button-primary" to="/records/new">
            <Plus aria-hidden="true" size={16} />
            New Record
          </Link>
        </div>
      </section>

      <section className="filter-panel" aria-label="Project filters">
        <form className="search-form" onSubmit={submitSearch}>
          <label className="field-control">
            <span>Search projects</span>
            <input
              aria-label="Search projects"
              value={searchText}
              onChange={(event) => setSearchText(event.target.value)}
            />
          </label>
          <button className="button button-secondary" type="submit">
            <SearchIcon aria-hidden="true" size={16} />
            Search
          </button>
          <Link
            className="button button-primary"
            to={buildSearchPageUrl({ type: "projects", q: searchText, status: statusFilter })}
          >
            <Search aria-hidden="true" size={16} />
            Search Hub
          </Link>
        </form>

        <label className="field-control">
          <span>Status</span>
          <select value={statusFilter} onChange={(event) => updateStatus(event.target.value)}>
            <option value="">All</option>
            {statusOptions.map((status) => (
              <option key={status} value={status}>
                {humanize(status)}
              </option>
            ))}
          </select>
        </label>

      <form className="search-form" onSubmit={openByUuid}>
          <label className="field-control">
            <span>Open project</span>
            <input
              aria-label="Project code, name, or UUID"
              placeholder="Project code, name, or UUID"
              value={directProjectId}
              onChange={(event) => {
                setDirectProjectId(event.target.value);
                setDirectProjectError("");
              }}
            />
          </label>
          <button className="button button-secondary" type="submit">
            <Search aria-hidden="true" size={16} />
            Open
          </button>
        </form>
      </section>
      {directProjectError && (
        <div className="admin-alert" role="alert">
          <strong>Open project</strong>
          <span>{directProjectError}</span>
        </div>
      )}

      <section className="table-panel" aria-labelledby="project-list-title">
        <div className="panel-heading">
          <div>
            <p className="section-kicker">Project queue</p>
            <h2 id="project-list-title">Published Projects</h2>
          </div>
          <StatusBadge tone={projectsQuery.isLoading ? "neutral" : "active"}>
            {projectsQuery.isLoading ? "Loading" : `${rawProjects.length} Projects`}
          </StatusBadge>
        </div>
      <DataTable
          data={rawProjects}
          emptyMessage={projectsQuery.isLoading ? "Loading projects." : "No projects match the selected filters."}
          columns={[
            {
              accessorKey: "name",
              header: "Project",
              cell: ({ row }) => (
                <Link to={`/projects/${row.original.id}`} className="text-link">
                  {row.original.name ?? row.original.record ?? row.original.id}
                </Link>
              )
            },
            {
              id: "record",
              header: "Source Record",
              cell: ({ row }) => row.original.record_code ?? row.original.record ?? "—"
            },
            {
              accessorKey: "status",
              header: "Status",
              cell: ({ row }) => (
                <StatusBadge tone={projectStatusTone(row.original.status)}>
                  {row.original.status ?? "Unknown"}
                </StatusBadge>
              )
            },
            {
              accessorKey: "description",
              header: "Description",
              cell: ({ row }) => (
                <span>{row.original.description ?? "No description provided."}</span>
              )
            },
            {
              id: "search",
              header: "Find",
              cell: ({ row }) => (
                <Link
                  className="text-link"
                  to={buildSearchPageUrl({
                    type: "projects",
                    q: row.original.record_code ?? row.original.name ?? row.original.id
                  })}
                >
                  Search
                </Link>
              )
            }
          ]}
        />
      </section>

      {projectsQuery.error && (
        <div className="admin-alert" role="alert">
          <strong>Project list failed</strong>
          <span>{errorMessage(projectsQuery.error)}</span>
        </div>
      )}

      <WorkloadView />
    </div>
  );
}

function projectsQueryString(searchParams: URLSearchParams) {
  const params = new URLSearchParams();

  const query = searchParams.get("q");
  const status = searchParams.get("status");
  const record = searchParams.get("record");

  if (query) {
    params.set("q", query);
  }
  if (status) {
    params.set("status", status);
  }
  if (record) {
    params.set("record", record);
  }

  const queryString = params.toString();
  return queryString ? `?${queryString}` : "";
}

function asProjectList(items?: ProjectListItem[] | PaginatedProjectList) {
  if (Array.isArray(items)) {
    return items;
  }

  return items?.results ?? [];
}

function uniqueSortedOptions<T>(rows: T[], pick: (row: T) => string | undefined) {
  return Array.from(new Set(rows.map((row) => pick(row)).filter(Boolean))).sort() as string[];
}

function humanize(value: string) {
  return value.replace(/[_-]+/g, " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

function projectStatusTone(status?: string) {
  if (status === "active" || status === "complete") {
    return "ready";
  }
  if (status === "planning") {
    return "review";
  }
  return "neutral";
}

function isUuid(value: string) {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value);
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Project list request failed.";
}
