/*
 * ===
 * File Summary
 * Path: frontend\src\features\workflows\TaskInbox.test.tsx
 * Type: typescript
 * Purpose: Frontend feature module implementing business flows and UI surfaces.
 * Primary responsibilities:
 * - Domain behavior is summarized for fast onboarding and avoids full-file reread.
 * - Core symbols: inferred from domain responsibilities
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

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useNavigate } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { TaskInbox } from "./TaskInbox";

function renderInbox(initialEntry = "/tasks") {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } }
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialEntry]}>
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

  it("filters tasks from dashboard URL parameters", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        if (input.toString() === "/api/workflow-tasks/?state=open") {
          return Response.json([
            {
              id: 1,
              key: "technical_review",
              title: "Technical review",
              assignee_user: 7,
              assignee_role: "Quality",
              due_date: "2026-06-06",
              state: "open",
              related_record: 101
            },
            {
              id: 2,
              key: "commercial_review",
              title: "Commercial review",
              assignee_user: 7,
              assignee_role: "Quality",
              due_date: "2026-06-06",
              state: "open",
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

        return Response.json({ detail: `Unexpected request ${input.toString()}` }, { status: 500 });
      })
    );

    renderInbox("/tasks?task_key=technical_review&due=overdue");

    expect(await screen.findByText("Technical review")).toBeInTheDocument();
    expect(screen.queryByText("Commercial review")).not.toBeInTheDocument();
    expect(screen.getByLabelText(/due/i)).toHaveValue("overdue");
  });

  it("keeps the due filter synchronized when dashboard links update the URL", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        if (input.toString() === "/api/workflow-tasks/?state=open") {
          return Response.json([
            {
              id: 1,
              key: "technical_review",
              title: "Overdue technical review",
              assignee_user: 7,
              assignee_role: "Quality",
              due_date: "2026-06-06",
              state: "open",
              related_record: 101
            },
            {
              id: 2,
              key: "technical_review",
              title: "Future technical review",
              assignee_user: 7,
              assignee_role: "Quality",
              due_date: "2026-06-20",
              state: "open",
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

        return Response.json({ detail: `Unexpected request ${input.toString()}` }, { status: 500 });
      })
    );
    const user = userEvent.setup();
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } }
    });

    function InboxWithNavigation() {
      const navigate = useNavigate();

      return (
        <>
          <button type="button" onClick={() => navigate("/tasks?task_key=technical_review&due=overdue")}>
            Dashboard overdue link
          </button>
          <TaskInbox currentUser="alex" currentRoles={["Quality"]} />
        </>
      );
    }

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={["/tasks?task_key=technical_review"]}>
          <InboxWithNavigation />
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(await screen.findByText("Overdue technical review")).toBeInTheDocument();
    expect(screen.getByText("Future technical review")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /dashboard overdue link/i }));

    expect(screen.getByLabelText(/due/i)).toHaveValue("overdue");
    expect(screen.getByText("Overdue technical review")).toBeInTheDocument();
    expect(screen.queryByText("Future technical review")).not.toBeInTheDocument();
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

  it("creates a new workflow task from the inbox action", async () => {
    const createdTasks: unknown[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = input.toString();

        if (url === "/api/workflow-tasks/?state=open") {
          return Response.json(createdTasks);
        }

        if (url === "/api/accounts/me/") {
          return Response.json({
            id: 7,
            username: "alex",
            roles: ["Quality"],
            groups: [{ name: "Quality" }]
          });
        }

        if (url === "/api/workflow-tasks/" && init?.method === "POST") {
          const payload = JSON.parse(init.body?.toString() ?? "{}");
          expect(payload).toMatchObject({
            title: "Investigate resin mismatch",
            related_record: "550e8400-e29b-41d4-a716-446655440000",
            assignee_user: 7
          });
          const task = {
            id: 99,
            title: payload.title,
            assignee_user: payload.assignee_user,
            due_date: payload.due_date,
            state: "open",
            related_record: payload.related_record
          };
          createdTasks.push(task);
          return Response.json(task, { status: 201 });
        }

        return Response.json({ detail: `Unexpected request ${url}` }, { status: 500 });
      })
    );
    const user = userEvent.setup();
    renderInbox();

    await user.click(await screen.findByRole("button", { name: /new task/i }));
    await user.type(screen.getByLabelText("Task Title"), "Investigate resin mismatch");
    await user.type(
      screen.getByLabelText("Related Record ID"),
      "550e8400-e29b-41d4-a716-446655440000"
    );
    await user.type(screen.getByLabelText("Task Assignee User ID"), "7");
    await user.click(screen.getByRole("button", { name: /create task/i }));

    expect(await screen.findByRole("status")).toHaveTextContent(/task created/i);
    expect(screen.getByText("Investigate resin mismatch")).toBeInTheDocument();
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

