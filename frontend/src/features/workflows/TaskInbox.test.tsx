import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { TaskInbox } from "./TaskInbox";

function renderInbox() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } }
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <TaskInbox currentUser="alex" currentRoles={["Quality"]} />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("TaskInbox", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("filters open workflow tasks by assignee, role, overdue status, object type, and state", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        if (input.toString() === "/api/workflow-tasks/?state=open") {
          return Response.json([
            {
              id: 1,
              title: "Approve resin spec",
              assignee_user: 7,
              assignee_role: "Quality",
              due_date: "2026-06-06",
              state: "open",
              related_record: 101,
              related_document: null,
              related_project: ""
            },
            {
              id: 2,
              title: "Review supplier dossier",
              assignee_user: 9,
              assignee_role: "Quality",
              due_date: "2026-06-12",
              state: "open",
              related_document: 55
            },
            {
              id: 3,
              title: "Archive trial package",
              assignee_user: 7,
              assignee_role: "Engineering",
              due_date: "2026-06-20",
              state: "blocked",
              related_record: 102
            }
          ]);
        }

        if (input.toString() === "/api/accounts/me/") {
          return Response.json({
            id: 7,
            username: "alex",
            roles: ["Quality"],
            groups: [{ name: "Quality" }]
          });
        }

        if (input.toString() === "/api/workflow-tasks/1/complete/" && init?.method === "POST") {
          return Response.json({ detail: "Guard failed" }, { status: 400 });
        }

        return Response.json({ detail: `Unexpected request ${input.toString()}` }, { status: 500 });
      })
    );

    const user = userEvent.setup();
    renderInbox();

    expect(await screen.findByText("Approve resin spec")).toBeInTheDocument();
    expect(screen.getByText("Review supplier dossier")).toBeInTheDocument();
    expect(screen.getByText("Archive trial package")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^find$/i })).not.toBeInTheDocument();

    await user.type(screen.getByLabelText(/search tasks/i), "supplier");
    expect(screen.queryByText("Approve resin spec")).not.toBeInTheDocument();
    expect(screen.getByText("Review supplier dossier")).toBeInTheDocument();
    expect(screen.queryByText("Archive trial package")).not.toBeInTheDocument();
    await user.clear(screen.getByLabelText(/search tasks/i));

    await user.selectOptions(screen.getByLabelText(/assignment/i), "me");
    expect(screen.getByText("Approve resin spec")).toBeInTheDocument();
    expect(screen.queryByText("Review supplier dossier")).not.toBeInTheDocument();
    expect(screen.getByText("Archive trial package")).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText(/assignment/i), "role");
    expect(screen.getByText("Approve resin spec")).toBeInTheDocument();
    expect(screen.getByText("Review supplier dossier")).toBeInTheDocument();
    expect(screen.queryByText("Archive trial package")).not.toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText(/assignment/i), "all");
    await user.selectOptions(screen.getByLabelText(/due/i), "overdue");
    expect(screen.getByText("Approve resin spec")).toBeInTheDocument();
    expect(screen.queryByText("Review supplier dossier")).not.toBeInTheDocument();
    expect(screen.queryByText("Archive trial package")).not.toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText(/due/i), "all");
    await user.selectOptions(screen.getByLabelText(/related object type/i), "document");
    expect(screen.queryByText("Approve resin spec")).not.toBeInTheDocument();
    expect(screen.getByText("Review supplier dossier")).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText(/related object type/i), "all");
    await user.selectOptions(screen.getByLabelText(/^state$/i), "blocked");
    const rows = within(screen.getByRole("table")).getAllByRole("row");
    expect(rows).toHaveLength(2);
    expect(screen.getByText("Archive trial package")).toBeInTheDocument();

    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith("/api/workflow-tasks/?state=open", expect.any(Object))
    );
  });

  it("shows completion errors when a workflow task cannot be completed", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        if (input.toString() === "/api/accounts/me/") {
          return Response.json({ id: 7, username: "alex", roles: ["Quality"] });
        }

        if (input.toString() === "/api/workflow-tasks/?state=open") {
          return Response.json([
            {
              id: 1,
              title: "Approve resin spec",
              assignee_user: 7,
              assignee_role: "Quality",
              due_date: "2026-06-06",
              state: "open",
              related_record: 101
            }
          ]);
        }

        if (input.toString() === "/api/workflow-tasks/1/complete/" && init?.method === "POST") {
          return Response.json({ detail: "Guard failed" }, { status: 400 });
        }

        return Response.json({ detail: `Unexpected request ${input.toString()}` }, { status: 500 });
      })
    );

    const user = userEvent.setup();
    renderInbox();

    await user.click(await screen.findByRole("button", { name: /complete/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/guard failed/i);
  });
});
