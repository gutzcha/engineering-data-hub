import { useQuery } from "@tanstack/react-query";

import { DataTable } from "../../components/DataTable";
import { StatusBadge } from "../../components/StatusBadge";
import { apiGet } from "../../lib/api";

export type WorkloadRow = {
  id?: string | number;
  assignee_user?: string | number | { id?: string | number; username?: string; name?: string; email?: string };
  username?: string;
  name?: string;
  role?: string;
  assignee?: string;
  open_tasks?: number;
  task_count?: number;
  overdue_tasks?: number;
  estimated_hours?: number;
  load?: number;
  capacity?: number;
};

type WorkloadViewProps = {
  compact?: boolean;
};

export function WorkloadView({ compact = false }: WorkloadViewProps) {
  const workloadQuery = useQuery({
    queryKey: ["projects", "workload"],
    queryFn: () => apiGet<WorkloadRow[]>("/projects/workload/")
  });

  const rows = workloadQuery.data ?? [];

  return (
    <section className="table-panel" aria-labelledby="workload-title">
      <div className="panel-heading">
        <div>
          <p className="section-kicker">Workload</p>
          <h2 id="workload-title">{compact ? "Team Workload" : "Project Workload"}</h2>
        </div>
        <StatusBadge tone={rows.length ? "active" : "neutral"}>
          {workloadQuery.isLoading ? "Loading" : rows.length}
        </StatusBadge>
      </div>

      {workloadQuery.error && (
        <div className="admin-alert project-inline-alert" role="alert">
          <strong>Workload failed</strong>
          <span>{errorMessage(workloadQuery.error)}</span>
        </div>
      )}

      <DataTable
        data={rows}
        emptyMessage={workloadQuery.isLoading ? "Loading workload." : "No workload rows returned."}
        columns={[
          {
            id: "assignee",
            header: "Assignee",
            cell: ({ row }) => assigneeLabel(row.original)
          },
          {
            id: "role",
            header: "Role",
            cell: ({ row }) => row.original.role ?? "Unassigned"
          },
          {
            id: "open",
            header: "Open",
            cell: ({ row }) => row.original.open_tasks ?? row.original.task_count ?? 0
          },
          {
            id: "overdue",
            header: "Overdue",
            cell: ({ row }) => (
              <StatusBadge tone={(row.original.overdue_tasks ?? 0) > 0 ? "blocked" : "ready"}>
                {row.original.overdue_tasks ?? 0}
              </StatusBadge>
            )
          },
          {
            id: "estimated",
            header: "Estimated",
            cell: ({ row }) => capacityLabel(row.original)
          }
        ]}
      />
    </section>
  );
}

function assigneeLabel(row: WorkloadRow) {
  if (typeof row.assignee_user === "object") {
    return row.assignee_user.name ?? row.assignee_user.username ?? row.assignee_user.email ?? row.assignee_user.id ?? "Unassigned";
  }

  return row.username ?? row.name ?? row.assignee ?? row.assignee_user ?? "Unassigned";
}

function capacityLabel(row: WorkloadRow) {
  if (row.estimated_hours !== undefined) {
    return `${row.estimated_hours} h`;
  }

  if (row.load === undefined && row.capacity === undefined) {
    return "Not tracked";
  }

  return `${row.load ?? 0}/${row.capacity ?? "?"}`;
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Project workload request failed.";
}
