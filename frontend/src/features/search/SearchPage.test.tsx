/*
 * ===
 * File Summary
 * Path: frontend\src\features\search\SearchPage.test.tsx
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
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AppRoutes } from "../../app/routes";

function renderSearchPage(initialEntries = ["/search?q=nylon"]) {
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

describe("SearchPage", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("groups search results and navigates from each result type", async () => {
    const requests: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = input.toString();
        requests.push(url);

        if (url === "/api/search/?q=nylon&type=all") {
          return Response.json({
            results: [
              {
                type: "record",
                code: "PROD-000101",
                title: "Nylon impact modifier",
                object_type_label: "Product",
                status: "draft",
                url: "/api/records/101/"
              },
              {
                type: "document",
                title: "Nylon release specification",
                record_code: "PROD-000101",
                status: "released",
                url: "/documents/202"
              },
              {
                type: "project",
                code: "PRJ-303",
                title: "Nylon trials",
                status: "active",
                url: "/api/projects/303/"
              },
              {
                type: "folder_event",
                title: "Unreviewed nylon folder change",
                path: "/Products/PROD-000101",
                status: "review",
                url: "/api/folder-events/404/"
              }
            ]
          });
        }

        return Response.json({ detail: `Unexpected request: ${url}` }, { status: 500 });
      })
    );
    const user = userEvent.setup();

    renderSearchPage();

    expect(await screen.findByRole("heading", { name: /search/i })).toBeInTheDocument();
    expect(requests).toContain("/api/search/?q=nylon&type=all");

    const records = await screen.findByRole("region", { name: /records/i });
    const documents = screen.getByRole("region", { name: /documents/i });
    const projects = screen.getByRole("region", { name: /projects/i });
    const folderEvents = screen.getByRole("region", { name: /folder review events/i });
    const resultLinks = [
      within(records).getByRole("link", { name: /nylon impact modifier/i }),
      within(documents).getByRole("link", { name: /nylon release specification/i }),
      within(projects).getByRole("link", { name: /nylon trials/i }),
      within(folderEvents).getByRole("link", { name: /unreviewed nylon folder change/i })
    ];

    expect(resultLinks.map((link) => link.getAttribute("href"))).toEqual([
      "/records/101",
      "/documents/202",
      "/projects/303",
      "/tasks/folder-events/404"
    ]);

    await user.click(resultLinks[0]);
    expect(await screen.findByRole("heading", { name: /record unavailable/i })).toBeInTheDocument();

    cleanup();
    renderSearchPage();
    const documentLink = await screen.findByRole("link", {
      name: /nylon release specification/i
    });
    await user.click(documentLink);
    expect(screen.getByRole("heading", { name: /document 202/i })).toBeInTheDocument();

    cleanup();
    renderSearchPage();
    const projectLink = await screen.findByRole("link", { name: /nylon trials/i });
    await user.click(projectLink);
    expect(screen.getByRole("heading", { name: /project 303/i })).toBeInTheDocument();

    cleanup();
    renderSearchPage();
    const folderEventLink = await screen.findByRole("link", {
      name: /unreviewed nylon folder change/i
    });
    await user.click(folderEventLink);
    expect(screen.getByRole("heading", { name: /folder event 404/i })).toBeInTheDocument();
  });

  it("renders only non-empty backend sections and ignores empty section buckets", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = input.toString();

        if (url === "/api/search/?type=all&status=active&object_type_key=product") {
          return Response.json({
            sections: [
              {
                key: "records",
                label: "Records",
                count: 1,
                items: [
                  {
                    type: "record",
                    id: 201,
                    title: "Active Product",
                    code: "PROD-002",
                    status: "active",
                    url: "/api/records/201/"
                  }
                ]
              },
              {
                key: "documents",
                label: "Documents",
                count: 0,
                items: []
              }
            ],
            count: 1
          });
        }

        return Response.json({ detail: `Unexpected request: ${url}` }, { status: 500 });
      })
    );

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } }
    });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={["/search?status=active&object_type_key=product"]}>
          <AppRoutes />
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(await screen.findByRole("heading", { name: /search/i })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: /records/i })).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: /documents/i })).not.toBeInTheDocument();
  });

  it("applies list filters to search query string", async () => {
    const requests: string[] = [];

    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = input.toString();
        requests.push(url);

        if (url === "/api/search/?type=all&status=active&object_type_key=product&resin_family=PP") {
          return Response.json({
            sections: [
              {
                key: "records",
                label: "Records",
                count: 1,
                items: [
                  {
                    type: "record",
                    id: 301,
                    title: "PP Grade",
                    code: "PROD-300",
                    status: "active",
                    url: "/api/records/301/"
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

    renderSearchPage(["/search"]);
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText(/object type/i), "product");
    await user.type(await screen.findByLabelText(/status/i), "active");
    await user.type(await screen.findByLabelText(/resin family/i), "PP{enter}");
    await user.click(screen.getByRole("button", { name: /search/i }));

    expect(requests).toEqual([
      "/api/search/?type=all&status=active&object_type_key=product&resin_family=PP"
    ]);
    expect(await screen.findByRole("region", { name: /records/i })).toBeInTheDocument();
  });
});

