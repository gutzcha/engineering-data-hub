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
});
