import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { FolderReviewInbox } from "./FolderReviewInbox";

function renderFolderReviewInbox(path = "/tasks/folder-events") {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } }
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/tasks/folder-events" element={<FolderReviewInbox />} />
          <Route path="/tasks/folder-events/:eventId" element={<FolderReviewInbox />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("FolderReviewInbox", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("loads selected event detail when the event is no longer pending", async () => {
    const requests: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = input.toString();
        requests.push(url);

        if (url === "/api/folder-events/?review_status=pending") {
          return Response.json([]);
        }

        if (url === "/api/folder-events/44/") {
          return Response.json({
            id: 44,
            event_type: "added",
            path: "Products/PROD-000044/accepted-specification.csv",
            matched_record: 101,
            managed_folder: null,
            review_status: "accepted",
            created_at: "2026-06-07T09:00:00Z"
          });
        }

        return Response.json({ detail: `Unexpected request: ${url}` }, { status: 500 });
      })
    );

    renderFolderReviewInbox("/tasks/folder-events/44");

    expect(await screen.findByRole("heading", { name: /folder event 44/i })).toBeInTheDocument();
    const selectedEvent = await screen.findByRole("region", { name: /selected folder event/i });
    expect(within(selectedEvent).getByText(/accepted-specification\.csv/i)).toBeInTheDocument();
    expect(requests).toContain("/api/folder-events/?review_status=pending");
    expect(requests).toContain("/api/folder-events/44/");
  });
});
