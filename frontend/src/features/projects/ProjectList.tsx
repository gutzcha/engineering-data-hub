import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Search } from "lucide-react";
import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { DataTable } from "../../components/DataTable";
import { StatusBadge } from "../../components/StatusBadge";
import { apiGet, apiPost } from "../../lib/api";
import { WorkloadView } from "./WorkloadView";

const projectUuidPattern =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

type ProjectListItem = {
  id: string;
  record?: string;
  name: string;
  description?: string;
  status?: string;
  owner?: string | number | null;
  owner_username?: string | null;
  task_count?: number;
  open_tasks?: number;
  target_date?: string | null;
  updated_at?: string;
};

type ProjectCreatePayload = {
  name: string;
  description: string;
  owner: number | null;
  target_date: string | null;
};

export function ProjectList() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [projectLookup, setProjectLookup] = useState("");
  const [validationError, setValidationError] = useState("");
  const [projectName, setProjectName] = useState("");
  const [projectDescription, setProjectDescription] = useState("");
  const [projectOwner, setProjectOwner] = useState("");
  const [projectTargetDate, setProjectTargetDate] = useState("");
  const projectsQuery = useQuery({
    queryKey: ["projects"],
    queryFn: () => apiGet<ProjectListItem[]>("/projects/")
  });
  const projects = projectsQuery.data ?? [];
  const createProject = useMutation({
    mutationFn: (payload: ProjectCreatePayload) => apiPost<ProjectListItem>("/projects/", payload),
    onSuccess: async () => {
      setProjectName("");
      setProjectDescription("");
      setProjectOwner("");
      setProjectTargetDate("");
      await queryClient.invalidateQueries({ queryKey: ["projects"] });
    }
  });

  function openProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const projectUuid = projectLookup.trim().toLowerCase();

    if (!projectUuidPattern.test(projectUuid)) {
      setValidationError("Enter a valid project UUID before opening a project.");
      return;
    }

    setValidationError("");
    navigate(`/projects/${encodeURIComponent(projectUuid)}`);
  }

  function submitProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    createProject.mutate({
      name: projectName.trim(),
      description: projectDescription.trim(),
      owner: projectOwner.trim() ? Number(projectOwner) : null,
      target_date: projectTargetDate || null
    });
  }

  return (
    <div className="page-stack project-page">
      <section className="workspace-header" aria-labelledby="projects-title">
        <div>
          <p className="section-kicker">Engineering project workspaces</p>
          <h1 id="projects-title">Projects</h1>
        </div>
        <StatusBadge tone={projects.length ? "active" : "neutral"}>
          {projectsQuery.isLoading ? "Loading" : `${projects.length} Projects`}
        </StatusBadge>
      </section>

      {projectsQuery.error && (
        <div className="admin-alert" role="alert">
          <strong>Projects failed</strong>
          <span>{errorMessage(projectsQuery.error)}</span>
        </div>
      )}

      <section className="table-panel" aria-labelledby="new-project-title">
        <div className="panel-heading">
          <div>
            <p className="section-kicker">New project</p>
            <h2 id="new-project-title">Create Project</h2>
          </div>
        </div>
        <form className="admin-form-grid" onSubmit={submitProject}>
          <label className="field-control">
            <span>Project Name</span>
            <input
              aria-label="Project Name"
              value={projectName}
              onChange={(event) => setProjectName(event.target.value)}
              required
            />
          </label>
          <label className="field-control field-control-wide">
            <span>Description</span>
            <textarea
              aria-label="Description"
              value={projectDescription}
              onChange={(event) => setProjectDescription(event.target.value)}
              rows={3}
            />
          </label>
          <label className="field-control">
            <span>Owner User ID</span>
            <input
              aria-label="Owner User ID"
              inputMode="numeric"
              min="1"
              type="number"
              value={projectOwner}
              onChange={(event) => setProjectOwner(event.target.value)}
            />
          </label>
          <label className="field-control">
            <span>Target Date</span>
            <input
              aria-label="Target Date"
              type="date"
              value={projectTargetDate}
              onChange={(event) => setProjectTargetDate(event.target.value)}
            />
          </label>
          <button
            className="button button-primary"
            type="submit"
            disabled={!projectName.trim() || createProject.isPending}
          >
            <Plus aria-hidden="true" size={16} />
            {createProject.isPending ? "Creating" : "Create Project"}
          </button>
        </form>
        {createProject.error && (
          <div className="admin-alert" role="alert">
            <strong>Project was not created</strong>
            <span>{errorMessage(createProject.error)}</span>
          </div>
        )}
      </section>

      <section className="table-panel" aria-labelledby="project-index-title">
        <div className="panel-heading">
          <div>
            <p className="section-kicker">Project index</p>
            <h2 id="project-index-title">Active Projects</h2>
          </div>
          <StatusBadge tone={projects.length ? "active" : "neutral"}>
            {projectsQuery.isLoading ? "Loading" : projects.length}
          </StatusBadge>
        </div>
        <DataTable
          data={projects}
          emptyMessage={projectsQuery.isLoading ? "Loading projects." : "No visible projects are available."}
          columns={[
            {
              id: "name",
              header: "Project",
              cell: ({ row }) => (
                <Link className="text-link" to={`/projects/${row.original.id}`}>
                  {row.original.name}
                </Link>
              )
            },
            {
              id: "status",
              header: "Status",
              cell: ({ row }) => (
                <StatusBadge tone={statusTone(row.original.status)}>
                  {humanize(row.original.status ?? "planning")}
                </StatusBadge>
              )
            },
            {
              id: "owner",
              header: "Owner",
              cell: ({ row }) => row.original.owner_username ?? row.original.owner ?? "Unassigned"
            },
            {
              id: "tasks",
              header: "Tasks",
              cell: ({ row }) =>
                `${row.original.open_tasks ?? 0} open / ${row.original.task_count ?? 0} total`
            },
            {
              id: "target",
              header: "Target",
              cell: ({ row }) => formatDate(row.original.target_date)
            },
            {
              id: "updated",
              header: "Updated",
              cell: ({ row }) => formatDate(row.original.updated_at)
            }
          ]}
        />
      </section>

      <section className="filter-panel" aria-label="Open project by UUID">
        <form className="search-form" onSubmit={openProject}>
          <label className="field-control field-control-wide">
            <span>Project UUID</span>
            <input
              aria-describedby={validationError ? "project-uuid-error" : undefined}
              aria-invalid={validationError ? "true" : undefined}
              aria-label="Project UUID"
              value={projectLookup}
              onChange={(event) => {
                setProjectLookup(event.target.value);
                if (validationError) {
                  setValidationError("");
                }
              }}
              placeholder="550e8400-e29b-41d4-a716-446655440000"
            />
          </label>
          <button className="button button-primary" type="submit">
            <Search aria-hidden="true" size={16} />
            Open
          </button>
        </form>
        {validationError && (
          <div className="admin-alert" id="project-uuid-error" role="alert">
            <strong>Project UUID required</strong>
            <span>{validationError}</span>
          </div>
        )}
      </section>

      <WorkloadView />
    </div>
  );
}

function statusTone(status?: string) {
  if (status === "active" || status === "complete") {
    return "ready";
  }

  if (status === "archived") {
    return "neutral";
  }

  return "review";
}

function humanize(value: string) {
  return value.replace(/[_-]+/g, " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

function formatDate(value?: string | null) {
  if (!value) {
    return "Not set";
  }

  return new Intl.DateTimeFormat("en", { dateStyle: "medium" }).format(new Date(value));
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Projects request failed.";
}
