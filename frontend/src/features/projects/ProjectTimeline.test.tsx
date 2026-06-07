import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ProjectTimeline } from "./ProjectTimeline";

function renderTimeline(mode: "timeline" | "dependencies" = "timeline") {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } }
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <ProjectTimeline projectId="31" mode={mode} />
    </QueryClientProvider>
  );
}

describe("ProjectTimeline", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("renders backend-shaped milestone, task, and dependency dates", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        if (input.toString() === "/api/projects/31/timeline/") {
          return Response.json({
            project: { id: 31, record: 101, name: "Thin wall redesign", status: "active" },
            milestones: [
              { id: 401, name: "Tooling freeze", target_date: "2026-06-10", completed_at: "2026-06-09T12:00:00Z" }
            ],
            tasks: [
              { id: 501, title: "Cut first mold trial", start_date: "2026-06-01", due_date: "2026-06-12" },
              { id: 601, title: "Release resin spec", start_date: "2026-06-02", due_date: "2026-06-08" }
            ],
            dependencies: [{ task: 501, depends_on: 601 }]
          });
        }

        return Response.json({ detail: `Unexpected request ${input.toString()}` }, { status: 500 });
      })
    );

    renderTimeline();

    expect(await screen.findByText("Tooling freeze")).toBeInTheDocument();
    expect(screen.getByText("Jun 10, 2026")).toBeInTheDocument();
    expect(screen.getByText("Done")).toBeInTheDocument();
    expect(screen.getByText("Cut first mold trial")).toBeInTheDocument();
    expect(screen.getByText(/Jun 1, 2026 to Jun 12, 2026/i)).toBeInTheDocument();
    expect(screen.getByText("Depends on 601")).toBeInTheDocument();
  });

  it("shows dependency creation errors", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        if (input.toString() === "/api/projects/31/timeline/") {
          return Response.json({
            project: { id: 31, record: 101, name: "Thin wall redesign", status: "active" },
            milestones: [],
            tasks: [
              { id: 501, title: "Cut first mold trial" },
              { id: 601, title: "Release resin spec" }
            ],
            dependencies: []
          });
        }

        if (input.toString() === "/api/project-tasks/501/dependencies/" && init?.method === "POST") {
          return Response.json({ detail: "Dependency would create a cycle" }, { status: 400 });
        }

        return Response.json({ detail: `Unexpected request ${input.toString()}` }, { status: 500 });
      })
    );

    const user = userEvent.setup();
    renderTimeline("dependencies");

    await user.selectOptions(
      await screen.findByLabelText(/add dependency for cut first mold trial/i),
      "601"
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(/dependency would create a cycle/i);
  });
});
