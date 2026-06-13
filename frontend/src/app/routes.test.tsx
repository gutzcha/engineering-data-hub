import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";

import { AppRoutes } from "./routes";

function renderRoutes(initialEntries = ["/"]) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } }
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={initialEntries}>
        <AppRoutes />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("App routes", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("navigates from home status card to prefiltered search route", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = input.toString();

        if (url === "/api/reports/dashboards/home-overview/?limit=10") {
          return Response.json({
            cards: [
              { key: "active", label: "Active", value: 3, filter: { status: "active" } }
            ],
            recent_records: []
          });
        }

        if (url === "/api/search/?type=all&status=active") {
          return Response.json({
            sections: [
              {
                key: "records",
                label: "Records",
                count: 1,
                items: [
                  {
                    type: "record",
                    id: 11,
                    title: "Active Product",
                    code: "PROD-001",
                    status: "active",
                    url: "/api/records/11/"
                  }
                ]
              }
            ],
            count: 1
          });
        }

        return Response.json({ detail: `Unexpected request: ${url}` }, { status: 500 });
      })
    );

    const user = userEvent.setup();
    renderRoutes();

    const activeCard = await screen.findByRole("button", { name: /open search filtered by active/i });
    await user.click(activeCard);

    expect(await screen.findByRole("heading", { name: /search/i })).toBeInTheDocument();
    expect(screen.getByText(/status: active/i)).toBeInTheDocument();
    expect(screen.getByRole("region", { name: /records/i })).toBeInTheDocument();
  });
});
