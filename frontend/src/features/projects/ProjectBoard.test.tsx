import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ProjectBoard } from "./ProjectBoard";

function renderBoard() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } }
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <ProjectBoard projectId="31" />
    </QueryClientProvider>
  );
}

describe("ProjectBoard", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("moves tasks across columns with the backend column id payload and refreshes board data", async () => {
    const requests: Array<{ body?: BodyInit | null; method: string; url: string }> = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = input.toString();
        const method = init?.method ?? "GET";
        requests.push({ body: init?.body, method, url });

        if (url === "/api/projects/31/board/") {
          return Response.json({
            project: { id: 31, code: "PRJ-31", title: "Thin wall redesign" },
            columns: [
              {
                id: 10,
                key: "todo",
                title: "To Do",
                tasks: [{ id: 501, title: "Cut first mold trial", state: "todo" }]
              },
              { id: 20, key: "doing", title: "Doing", tasks: [] },
              { id: 30, key: "done", title: "Done", tasks: [] }
            ],
            unassigned_tasks: []
          });
        }

        if (url === "/api/project-tasks/501/move/" && method === "PATCH") {
          return Response.json({ id: 501, title: "Cut first mold trial", state: "doing" });
        }

        return Response.json({ detail: `Unexpected request ${method} ${url}` }, { status: 500 });
      })
    );

    const user = userEvent.setup();
    renderBoard();

    expect(await screen.findByText("Cut first mold trial")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "To Do" })).toBeInTheDocument();
    const task = screen.getByRole("article", { name: /cut first mold trial/i });
    await user.selectOptions(within(task).getByLabelText(/move task/i), "20");

    await waitFor(() => {
      const moveRequest = requests.find(
        (request) => request.method === "PATCH" && request.url === "/api/project-tasks/501/move/"
      );
      expect(moveRequest).toBeDefined();
      expect(JSON.parse(moveRequest?.body?.toString() ?? "{}")).toEqual({
        column: 20,
        sort_order: 0
      });
    });

    await waitFor(() => {
      expect(requests.filter((request) => request.url === "/api/projects/31/board/")).toHaveLength(2);
    });
  });

  it("shows move errors when the backend rejects a board update", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = input.toString();
        const method = init?.method ?? "GET";

        if (url === "/api/projects/31/board/") {
          return Response.json({
            project: { id: 31, name: "Thin wall redesign" },
            columns: [
              {
                id: 10,
                key: "todo",
                title: "To Do",
                tasks: [{ id: 501, title: "Cut first mold trial" }]
              },
              { id: 20, key: "doing", title: "Doing", tasks: [] }
            ],
            unassigned_tasks: []
          });
        }

        if (url === "/api/project-tasks/501/move/" && method === "PATCH") {
          return Response.json({ detail: "Column is closed" }, { status: 400 });
        }

        return Response.json({ detail: `Unexpected request ${method} ${url}` }, { status: 500 });
      })
    );

    const user = userEvent.setup();
    renderBoard();

    const task = await screen.findByRole("article", { name: /cut first mold trial/i });
    await user.selectOptions(within(task).getByLabelText(/move task/i), "20");

    expect(await screen.findByRole("alert")).toHaveTextContent(/column is closed/i);
  });

  it("updates task status and assignee from the board card", async () => {
    const requests: Array<{ body?: BodyInit | null; method: string; url: string }> = [];

    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = input.toString();
        const method = init?.method ?? "GET";
        requests.push({ body: init?.body, method, url });

        if (url === "/api/projects/31/board/") {
          return Response.json({
            project: { id: 31, code: "PRJ-31", title: "Thin wall redesign" },
            columns: [
              {
                id: 10,
                key: "todo",
                title: "To Do",
                tasks: [
                  {
                    id: 501,
                    title: "Cut first mold trial",
                    state: "todo",
                    assignee_user: null
                  }
                ]
              },
              { id: 20, key: "doing", title: "Doing", tasks: [] }
            ],
            unassigned_tasks: []
          });
        }

        if (url === "/api/project-tasks/501/" && method === "PATCH") {
          return Response.json({
            id: 501,
            title: "Cut first mold trial",
            state: "in_progress",
            assignee_user: 7
          });
        }

        return Response.json({ detail: `Unexpected request ${method} ${url}` }, { status: 500 });
      })
    );

    const user = userEvent.setup();
    renderBoard();

    const task = await screen.findByRole("article", { name: /cut first mold trial/i });
    await user.selectOptions(within(task).getByLabelText(/task state/i), "in_progress");
    await user.type(within(task).getByLabelText(/assignee user id/i), "7");
    await user.click(within(task).getByRole("button", { name: /save task/i }));

    await waitFor(() => {
      const updateRequest = requests.find(
        (request) => request.method === "PATCH" && request.url === "/api/project-tasks/501/"
      );
      expect(updateRequest).toBeDefined();
      expect(JSON.parse(updateRequest?.body?.toString() ?? "{}")).toEqual({
        assignee_user: 7,
        state: "in_progress"
      });
    });
  });
});
