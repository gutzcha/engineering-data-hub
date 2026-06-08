import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ProjectList } from "./ProjectList";

function renderProjectList() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } }
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/projects"]}>
        <Routes>
          <Route path="/projects" element={<ProjectList />} />
          <Route path="/projects/:projectId" element={<h1>Project Detail Route</h1>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("ProjectList", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("requires a project UUID before navigating to project detail", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        if (input.toString() === "/api/projects/") {
          return Response.json([]);
        }

        if (input.toString() === "/api/projects/workload/") {
          return Response.json([]);
        }

        return Response.json({ detail: `Unexpected request ${input.toString()}` }, { status: 500 });
      })
    );

    const user = userEvent.setup();
    renderProjectList();

    const input = screen.getByLabelText(/project uuid/i);
    expect(input).toHaveAttribute("placeholder", "550e8400-e29b-41d4-a716-446655440000");

    await user.type(input, "PRJ-31");
    await user.click(screen.getByRole("button", { name: /open/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/enter a valid project uuid/i);
    expect(screen.queryByRole("heading", { name: /project detail route/i })).not.toBeInTheDocument();

    await user.clear(input);
    await user.type(input, "550E8400-E29B-41D4-A716-446655440000");
    await user.click(screen.getByRole("button", { name: /open/i }));

    expect(await screen.findByRole("heading", { name: /project detail route/i })).toBeInTheDocument();
  });

  it("lists visible projects as clickable project links", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        if (input.toString() === "/api/projects/") {
          return Response.json([
            {
              id: "550e8400-e29b-41d4-a716-446655440000",
              record: "record-1",
              name: "Mold Transfer Project",
              status: "active",
              task_count: 5,
              open_tasks: 3,
              updated_at: "2026-06-08T10:00:00Z"
            }
          ]);
        }

        if (input.toString() === "/api/projects/workload/") {
          return Response.json([]);
        }

        return Response.json({ detail: `Unexpected request ${input.toString()}` }, { status: 500 });
      })
    );

    renderProjectList();

    const projectLink = await screen.findByRole("link", { name: /mold transfer project/i });
    expect(projectLink).toHaveAttribute(
      "href",
      "/projects/550e8400-e29b-41d4-a716-446655440000"
    );
    expect(screen.getByText("3 open / 5 total")).toBeInTheDocument();
  });

  it("creates a new project from the project workspace", async () => {
    const projects: Array<Record<string, unknown>> = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        if (input.toString() === "/api/projects/" && (!init?.method || init.method === "GET")) {
          return Response.json(projects);
        }

        if (input.toString() === "/api/projects/" && init?.method === "POST") {
          const body = JSON.parse(String(init.body));
          const created = {
            id: "550e8400-e29b-41d4-a716-446655440001",
            record: "record-2",
            name: body.name,
            description: body.description,
            status: "planning",
            owner: Number(body.owner),
            owner_username: "qa_owner",
            task_count: 0,
            open_tasks: 0,
            updated_at: "2026-06-08T10:00:00Z"
          };
          projects.push(created);
          return Response.json(created, { status: 201 });
        }

        if (input.toString() === "/api/projects/workload/") {
          return Response.json([]);
        }

        return Response.json({ detail: `Unexpected request ${input.toString()}` }, { status: 500 });
      })
    );

    const user = userEvent.setup();
    renderProjectList();

    await user.type(await screen.findByLabelText(/project name/i), "Operator Project");
    await user.type(screen.getByLabelText(/^description$/i), "Created from UI");
    await user.type(screen.getByLabelText(/owner user id/i), "7");
    await user.click(screen.getByRole("button", { name: /create project/i }));

    expect(await screen.findByRole("link", { name: /operator project/i })).toHaveAttribute(
      "href",
      "/projects/550e8400-e29b-41d4-a716-446655440001"
    );
  });
});
