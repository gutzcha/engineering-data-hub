import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DashboardPage } from "./DashboardPage";

function renderDashboardPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } }
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("DashboardPage", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("loads a configured dashboard and runs a saved list view", async () => {
    const requests: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = input.toString();
        requests.push(url);

        if (url === "/api/config/active/") {
          return Response.json({
            data: {
              object_types: [
                {
                  key: "product",
                  label: "Product",
                  fields: [{ key: "commercial_name", label: "Commercial Name" }]
                }
              ],
              dashboards: [{ key: "quality_operations", name: "Quality Operations" }]
            }
          });
        }

        if (url === "/api/saved-views/") {
          return Response.json({
            results: [
              {
                id: 5,
                name: "Released Products",
                filters: [{ type: "status", value: "released" }],
                columns: ["code", "title", "data.commercial_name"],
                sort: ["code"]
              }
            ]
          });
        }

        if (url === "/api/dashboards/quality_operations/") {
          return Response.json({
            id: 7,
            name: "Quality Operations",
            description: "Release and review health",
            config: {},
            widgets: [
              {
                id: 11,
                title: "Records By Status",
                widget_type: "count_by_status",
                config: {},
                sort_order: 1,
                data: { items: [{ key: "draft", count: 2 }, { key: "released", count: 3 }] }
              },
              {
                id: 12,
                title: "Recent Changes",
                widget_type: "recent_changes",
                config: {},
                sort_order: 2,
                data: {
                  items: [
                    {
                      id: 99,
                      action: "record.updated",
                      object_type: "record",
                      object_id: "rec-1",
                      actor_username: "auditor",
                      created_at: "2026-06-07T09:00:00Z"
                    }
                  ]
                }
              }
            ]
          });
        }

        if (url === "/api/saved-views/5/results/?limit=50") {
          return Response.json({
            count: 1,
            results: [
              {
                id: "rec-1",
                code: "PROD-000042",
                title: "Released Film",
                "data.commercial_name": "Clear release film"
              }
            ]
          });
        }

        return Response.json({ detail: `Unexpected request: ${url}` }, { status: 500 });
      })
    );
    const user = userEvent.setup();

    renderDashboardPage();

    expect(
      await screen.findByRole("heading", { level: 1, name: /quality operations/i })
    ).toBeInTheDocument();
    expect(screen.getByText(/release and review health/i)).toBeInTheDocument();
    const widget = screen.getByRole("region", { name: /records by status/i });
    expect(within(widget).getByText(/draft/i)).toBeInTheDocument();
    expect(within(widget).getByText("2")).toBeInTheDocument();
    expect(within(widget).getByText(/released/i)).toBeInTheDocument();
    expect(screen.getByText(/record.updated/i)).toBeInTheDocument();
    const savedViewStatus = screen.getByLabelText(/saved view status/i);
    expect(within(savedViewStatus).getByRole("option", { name: "Archived" })).toHaveValue(
      "archived"
    );
    expect(
      within(savedViewStatus).queryByRole("option", { name: "Blocked" })
    ).not.toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText(/^saved view$/i), "5");
    await user.click(screen.getByRole("button", { name: /run saved view/i }));

    expect(await screen.findByText("PROD-000042")).toBeInTheDocument();
    expect(screen.getByText("Released Film")).toBeInTheDocument();
    expect(screen.getByText("Clear release film")).toBeInTheDocument();
    expect(requests).toContain("/api/dashboards/quality_operations/");
    expect(requests).toContain("/api/saved-views/5/results/?limit=50");
  });

  it("makes count dashboard widget rows clickable filters", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = input.toString();

        if (url === "/api/config/active/") {
          return Response.json({
            data: {
              object_types: [{ key: "product", label: "Product", fields: [] }],
              dashboards: [{ key: "quality_operations", name: "Quality Operations" }]
            }
          });
        }

        if (url === "/api/saved-views/") {
          return Response.json({ results: [] });
        }

        if (url === "/api/dashboards/quality_operations/") {
          return Response.json({
            id: 7,
            name: "Quality Operations",
            widgets: [
              {
                id: 11,
                title: "Records By Status",
                widget_type: "count_by_status",
                data: { items: [{ key: "archived", count: 4 }, { key: "draft", count: 8 }] }
              },
              {
                id: 12,
                title: "Records By Object Type",
                widget_type: "count_by_object_type",
                data: { items: [{ key: "raw_material", count: 3 }] }
              },
              {
                id: 13,
                title: "Projects By Status",
                widget_type: "count_by_status",
                config: { filters: [{ type: "object_type", value: "project" }] },
                data: { items: [{ key: "active", count: 2 }] }
              }
            ]
          });
        }

        return Response.json({ detail: `Unexpected request: ${url}` }, { status: 500 });
      })
    );

    renderDashboardPage();

    const statusWidget = await screen.findByRole("region", { name: /records by status/i });
    expect(within(statusWidget).getByRole("link", { name: /archived/i })).toHaveAttribute(
      "href",
      "/records?status=archived"
    );
    expect(within(statusWidget).getByRole("link", { name: /draft/i })).toHaveAttribute(
      "href",
      "/records?status=draft"
    );

    const objectTypeWidget = screen.getByRole("region", { name: /records by object type/i });
    expect(within(objectTypeWidget).getByRole("link", { name: /raw material/i })).toHaveAttribute(
      "href",
      "/records?object_type_key=raw_material"
    );

    const scopedStatusWidget = screen.getByRole("region", { name: /projects by status/i });
    expect(within(scopedStatusWidget).getByRole("link", { name: /active/i })).toHaveAttribute(
      "href",
      "/records?object_type_key=project&status=active"
    );
  });
});
