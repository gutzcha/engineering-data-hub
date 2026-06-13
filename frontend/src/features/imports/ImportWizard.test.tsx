/*
 * ===
 * File Summary
 * Path: frontend\src\features\imports\ImportWizard.test.tsx
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
import { afterEach, describe, expect, it, vi } from "vitest";

import { ImportWizard } from "./ImportWizard";

const activeConfig = {
  id: 1,
  version: 7,
  data: {
    object_types: [
      {
        key: "product",
        label: "Product",
        plural_label: "Products",
        title_field: "commercial_name",
        fields: [
          {
            key: "commercial_name",
            label: "Commercial Name",
            type: "text",
            required: true
          },
          {
            key: "resin_family",
            label: "Resin Family",
            type: "choice",
            options: ["PP", "HDPE"]
          }
        ]
      }
    ]
  }
};

type CapturedImportRequest = {
  mapping?: unknown;
  method: string;
  sourceFile?: string;
  targetObjectType?: string;
  url: string;
};

function renderWizard() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } }
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <ImportWizard />
    </QueryClientProvider>
  );
}

describe("ImportWizard", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("uploads a file, maps columns, runs dry-run, and shows row errors", async () => {
    const requests: CapturedImportRequest[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = input.toString();
        const method = init?.method ?? "GET";
        requests.push(captureRequest(url, method, init?.body));

        if (url === "/api/config/active/" && method === "GET") {
          return Response.json(activeConfig);
        }

        if (url === "/api/imports/jobs/" && method === "POST") {
          return Response.json(
            {
              id: 77,
              target_object_type: "product",
              mapping: requests[requests.length - 1]?.mapping,
              state: "pending"
            },
            { status: 201 }
          );
        }

        if (url === "/api/imports/jobs/77/dry-run/" && method === "POST") {
          return Response.json({
            summary: { create: 1, update: 0, errors: 1 },
            creates: [
              {
                row_number: 2,
                code: "",
                data: { commercial_name: "Clear film", resin_family: "PP" }
              }
            ],
            updates: [],
            error_rows: [
              {
                row_number: 3,
                code: "",
                errors: { commercial_name: ["This field is required."] }
              }
            ]
          });
        }

        return Response.json({ detail: `Unexpected request: ${method} ${url}` }, { status: 500 });
      })
    );
    const user = userEvent.setup();
    const csv = new File(["Code,Commercial Name,Family\n,Clear film,PP\n,,HDPE"], "products.csv", {
      type: "text/csv"
    });

    renderWizard();

    expect(await screen.findByRole("heading", { name: /import wizard/i })).toBeInTheDocument();
    await user.upload(screen.getByLabelText(/source file/i), csv);
    expect(await screen.findAllByRole("option", { name: "Family" })).not.toHaveLength(0);
    await user.selectOptions(screen.getByLabelText(/object type/i), "product");
    await user.selectOptions(screen.getByLabelText(/code source column/i), "Code");
    await user.selectOptions(screen.getByLabelText(/commercial name source column/i), "Commercial Name");
    await user.selectOptions(screen.getByLabelText(/resin family source column/i), "Family");

    await user.click(screen.getByRole("button", { name: /run dry-run/i }));

    expect(await screen.findByText(/1 create/i)).toBeInTheDocument();
    expect(screen.getByText(/1 error/i)).toBeInTheDocument();
    const errors = screen.getByRole("list", { name: /import row errors/i });
    expect(within(errors).getByText(/row 3/i)).toBeInTheDocument();
    expect(within(errors).getByText(/commercial_name/i)).toBeInTheDocument();
    expect(within(errors).getByText(/this field is required/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /apply import/i })).toBeDisabled();
    expect(requests.find((request) => request.url === "/api/imports/jobs/")).toMatchObject({
      method: "POST",
      sourceFile: "products.csv",
      targetObjectType: "product",
      mapping: {
        columns: {
          Code: "code",
          "Commercial Name": "commercial_name",
          Family: "resin_family"
        }
      }
    });
  });

  it("applies a clean dry-run with the managed-folder option", async () => {
    const requests: CapturedImportRequest[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = input.toString();
        const method = init?.method ?? "GET";
        requests.push(captureRequest(url, method, init?.body));

        if (url === "/api/config/active/" && method === "GET") {
          return Response.json(activeConfig);
        }

        if (url === "/api/imports/jobs/" && method === "POST") {
          return Response.json({ id: 88, target_object_type: "product", state: "pending" }, { status: 201 });
        }

        if (url === "/api/imports/jobs/88/dry-run/" && method === "POST") {
          return Response.json({
            summary: { create: 2, update: 0, errors: 0 },
            creates: [],
            updates: [],
            error_rows: []
          });
        }

        if (url === "/api/imports/jobs/88/apply/" && method === "POST") {
          return Response.json({ created: 2, updated: 0 });
        }

        return Response.json({ detail: `Unexpected request: ${method} ${url}` }, { status: 500 });
      })
    );
    const user = userEvent.setup();
    const csv = new File(["Commercial Name\nClear film\nBlue film"], "clean-products.csv", {
      type: "text/csv"
    });

    renderWizard();

    await screen.findByRole("heading", { name: /import wizard/i });
    await user.upload(screen.getByLabelText(/source file/i), csv);
    expect(await screen.findAllByRole("option", { name: "Commercial Name" })).not.toHaveLength(0);
    await user.selectOptions(screen.getByLabelText(/commercial name source column/i), "Commercial Name");
    await user.click(screen.getByRole("checkbox", { name: /create managed folders/i }));
    await user.click(screen.getByRole("button", { name: /run dry-run/i }));
    await user.click(await screen.findByRole("button", { name: /apply import/i }));

    expect(await screen.findByText(/applied 2 created \/ 0 updated/i)).toBeInTheDocument();
    await waitFor(() =>
      expect(requests.find((request) => request.url === "/api/imports/jobs/88/apply/")).toMatchObject({
        method: "POST"
      })
    );
    expect(requests.find((request) => request.url === "/api/imports/jobs/88/apply/")?.mapping).toEqual({
      create_managed_folders: true
    });
  });
});

function captureRequest(url: string, method: string, body?: BodyInit | null): CapturedImportRequest {
  if (typeof FormData !== "undefined" && body instanceof FormData) {
    const sourceFile = body.get("source_file");
    return {
      method,
      url,
      sourceFile: sourceFile instanceof File ? sourceFile.name : undefined,
      targetObjectType: String(body.get("target_object_type") ?? ""),
      mapping: JSON.parse(String(body.get("mapping") ?? "{}"))
    };
  }

  if (typeof body === "string") {
    return { method, url, mapping: JSON.parse(body) };
  }

  return { method, url };
}

