import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ProjectDetail } from "./ProjectDetail";

function renderProjectDetail(projectId = "550e8400-e29b-41d4-a716-446655440000") {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } }
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/projects/${projectId}`]}>
        <Routes>
          <Route path="/projects/:projectId" element={<ProjectDetail />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("ProjectDetail", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("updates project status and owner from the overview tab", async () => {
    const projectId = "550e8400-e29b-41d4-a716-446655440000";
    const requests: Array<{ body?: BodyInit | null; method: string; url: string }> = [];

    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = input.toString();
        const method = init?.method ?? "GET";
        requests.push({ body: init?.body, method, url });

        if (url === `/api/projects/${projectId}/`) {
          if (method === "PATCH") {
            return Response.json({
              id: projectId,
              name: "Thin wall redesign",
              description: "Operator updated",
              status: "active",
              owner: 7,
              owner_username: "qa_owner",
              target_date: "2026-07-01"
            });
          }

          return Response.json({
            id: projectId,
            name: "Thin wall redesign",
            description: "Initial scope",
            status: "planning",
            owner: null,
            target_date: null
          });
        }

        if (url === `/api/projects/${projectId}/board/`) {
          return Response.json({ project: { id: projectId, name: "Thin wall redesign" }, columns: [] });
        }

        if (url === `/api/projects/${projectId}/timeline/`) {
          return Response.json({
            project: { id: projectId, name: "Thin wall redesign", status: "planning" },
            milestones: [],
            tasks: [],
            dependencies: []
          });
        }

        if (url === "/api/projects/workload/") {
          return Response.json([]);
        }

        return Response.json({ detail: `Unexpected request ${method} ${url}` }, { status: 500 });
      })
    );

    const user = userEvent.setup();
    renderProjectDetail(projectId);

    await user.selectOptions(await screen.findByLabelText(/project status/i), "active");
    await user.type(screen.getByLabelText(/owner user id/i), "7");
    await user.type(screen.getByLabelText(/^description$/i), "Operator updated");
    await user.click(screen.getByRole("button", { name: /save project/i }));

    await waitFor(() => {
      const updateRequest = requests.find(
        (request) => request.method === "PATCH" && request.url === `/api/projects/${projectId}/`
      );
      expect(updateRequest).toBeDefined();
      expect(JSON.parse(updateRequest?.body?.toString() ?? "{}")).toMatchObject({
        description: "Initial scopeOperator updated",
        owner: 7,
        status: "active"
      });
    });
  });

  it("does not overwrite unsaved project edits when late project data arrives", async () => {
    const projectId = "550e8400-e29b-41d4-a716-446655440001";
    const requests: Array<{ body?: BodyInit | null; method: string; url: string }> = [];
    let resolveProjectGet: (response: Response) => void = () => undefined;

    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = input.toString();
        const method = init?.method ?? "GET";
        requests.push({ body: init?.body, method, url });

        if (url === `/api/projects/${projectId}/`) {
          if (method === "PATCH") {
            return Response.json({
              id: projectId,
              name: "Late project data",
              description: "",
              status: "active",
              owner: null,
              target_date: null
            });
          }

          return new Promise<Response>((resolve) => {
            resolveProjectGet = resolve;
          });
        }

        if (url === `/api/projects/${projectId}/board/`) {
          return Response.json({ project: { id: projectId, name: "Late project data" }, columns: [] });
        }

        if (url === `/api/projects/${projectId}/timeline/`) {
          return Response.json({
            project: { id: projectId, name: "Late project data", status: "planning" },
            milestones: [],
            tasks: [],
            dependencies: []
          });
        }

        if (url === "/api/projects/workload/") {
          return Response.json([]);
        }

        return Response.json({ detail: `Unexpected request ${method} ${url}` }, { status: 500 });
      })
    );

    const user = userEvent.setup();
    renderProjectDetail(projectId);

    await user.selectOptions(await screen.findByLabelText(/project status/i), "active");
    resolveProjectGet(
      Response.json({
        id: projectId,
        name: "Late project data",
        description: "",
        status: "planning",
        owner: null,
        target_date: null
      })
    );
    await waitFor(() => expect(screen.getByLabelText(/project status/i)).toHaveValue("active"));

    await user.click(screen.getByRole("button", { name: /save project/i }));

    await waitFor(() => {
      const updateRequest = requests.find(
        (request) => request.method === "PATCH" && request.url === `/api/projects/${projectId}/`
      );
      expect(updateRequest).toBeDefined();
      expect(JSON.parse(updateRequest?.body?.toString() ?? "{}")).toMatchObject({
        status: "active"
      });
    });
  });
});
