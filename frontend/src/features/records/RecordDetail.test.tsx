/*
 * ===
 * File Summary
 * Path: frontend\src\features\records\RecordDetail.test.tsx
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
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { RecordDetail } from "./RecordDetail";

const activeConfiguration = {
  id: 1,
  version: 3,
  data: {
    object_types: [
      {
        key: "product",
        label: "Product",
        plural_label: "Products",
        title_field: "commercial_name",
        folder_template_key: "product_release",
        default_workflow_key: "engineering_release",
        fields: [
          {
            key: "commercial_name",
            label: "Commercial Name",
            type: "text",
            required: true,
            searchable: true
          },
          {
            key: "resin_family",
            label: "Resin Family",
            type: "choice",
            options: ["PP", "HDPE", "Nylon"]
          },
          {
            key: "melt_flow_index",
            label: "Melt Flow Index",
            type: "number"
          },
          {
            key: "flame_retardant",
            label: "Flame Retardant",
            type: "boolean"
          },
          {
            key: "approved_additives",
            label: "Approved Additives",
            type: "multi_choice",
            options: ["UV Stabilizer", "Impact Modifier", "Color Masterbatch"]
          }
        ]
      }
    ],
    form_layouts: [
      {
        key: "product_release",
        object_type_key: "product",
        sections: [
          {
            label: "Identity",
            fields: ["commercial_name", "resin_family"]
          },
          {
            label: "Testing",
            fields: ["melt_flow_index", "flame_retardant", "approved_additives"]
          }
        ]
      }
    ],
    folder_templates: [],
    workflows: []
  }
};

const productRecord = {
  id: 101,
  code: "PROD-000101",
  object_type_key: "product",
  status: "draft",
  title: "Clear Film 720",
  data: {
    commercial_name: "Clear Film 720",
    resin_family: "PP",
    melt_flow_index: 18.4,
    flame_retardant: true,
    approved_additives: ["UV Stabilizer"]
  },
  documents: [
    {
      id: 201,
      title: "Release spec",
      document_type: "specification",
      state: "draft",
      current_revision: {
        id: 1,
        revision_label: "A",
        extraction_status: "complete",
        state: "draft",
        created_at: "2026-06-07T08:00:00Z"
      }
    }
  ],
  folder: {
    path: "/Products/PROD-000101-Clear Film 720/Release",
    state: "synced",
    recent_changes: [
      {
        id: 8,
        summary: "New COA detected",
        detected_at: "2026-06-07T08:30:00Z"
      }
    ]
  },
  project_links: [{ id: 31, code: "PRJ-31", title: "Thin wall redesign" }]
};

function renderRecordDetail() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } }
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/records/101"]}>
        <Routes>
          <Route path="/records/:recordId" element={<RecordDetail />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("RecordDetail", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("renders configured form fields and saves edited record values", async () => {
    const requests: Array<{
      body?: BodyInit | null;
      headers?: HeadersInit;
      method: string;
      url: string;
    }> = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = input.toString();
        const method = init?.method ?? "GET";
        requests.push({
          body: init?.body,
          headers: init?.headers,
          method,
          url
        });

        if (url === "/api/config/active/") {
          return Response.json(activeConfiguration);
        }

        if (url === "/api/records/101/") {
          if (method === "PATCH") {
            return Response.json({
              ...productRecord,
              data: {
                ...productRecord.data,
                ...JSON.parse(init?.body?.toString() ?? "{}").data
              }
            });
          }

          return Response.json(productRecord);
        }

        if (url === "/api/records/101/graph/") {
          return Response.json({
            nodes: [
              { id: "101", label: "Clear Film 720", type: "record" },
              { id: "31", label: "Thin wall redesign", type: "project" }
            ],
            edges: [{ source: "101", target: "31", label: "used by" }]
          });
        }

        if (url === "/api/records/101/workflow/") {
          return Response.json({
            state: "draft",
            available_transitions: [
              { key: "request_approval", label: "Submit for Review", to_state: "review" }
            ]
          });
        }

        if (url === "/api/documents/" && method === "POST") {
          return Response.json(
            {
              id: 202,
              title: "Process notes.pdf",
              status: "draft",
              extraction_status: "queued",
              revisions: []
            },
            { status: 201 }
          );
        }

        if (url === "/api/documents/201/revisions/1/release/" && method === "POST") {
          return Response.json({
            id: 1,
            revision_label: "A",
            extraction_status: "complete",
            state: "released"
          });
        }

        if (url === "/api/records/101/workflow/request_approval/" && method === "POST") {
          return Response.json({
            state: "review",
            available_transitions: []
          });
        }

        if (url === "/api/folder-events/?record=101") {
          return Response.json(productRecord.folder.recent_changes);
        }

        if (url === "/api/folder-events/8/accept/" && method === "POST") {
          return Response.json({ ...productRecord.folder.recent_changes[0], review_status: "accepted" });
        }

        if (url === "/api/folder-events/8/ignore/" && method === "POST") {
          return Response.json({ ...productRecord.folder.recent_changes[0], review_status: "ignored" });
        }

        if (url === "/api/audit/records/101/") {
          return Response.json({
            results: [
              { id: 1, action: "created", actor: "Quality", created_at: "2026-06-06T10:00:00Z" }
            ]
          });
        }

        return Response.json({ detail: `Unexpected request: ${method} ${url}` }, { status: 500 });
      })
    );
    const user = userEvent.setup();

    renderRecordDetail();

    expect(await screen.findByRole("heading", { name: /clear film 720/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /identity/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/commercial name/i)).toHaveValue("Clear Film 720");
    expect(screen.getByLabelText(/resin family/i)).toHaveValue("PP");
    expect(screen.getByLabelText(/melt flow index/i)).toHaveValue(18.4);
    expect(screen.getByLabelText(/flame retardant/i)).toBeChecked();
    expect(screen.getByLabelText(/approved additives/i)).toHaveValue(["UV Stabilizer"]);
    expect(screen.getByText("/Products/PROD-000101-Clear Film 720/Release")).toBeInTheDocument();
    expect(screen.getByText(/release spec/i)).toBeInTheDocument();
    expect(screen.getByText(/submit for review/i)).toBeInTheDocument();
    expect(screen.getAllByText(/thin wall redesign/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/created/i)).toBeInTheDocument();

    await user.clear(screen.getByLabelText(/commercial name/i));
    await user.type(screen.getByLabelText(/commercial name/i), "Clear Film 820");
    await user.selectOptions(screen.getByLabelText(/resin family/i), "Nylon");
    await user.deselectOptions(screen.getByLabelText(/approved additives/i), "UV Stabilizer");
    await user.selectOptions(screen.getByLabelText(/approved additives/i), [
      "Impact Modifier",
      "Color Masterbatch"
    ]);
    await user.click(screen.getByRole("button", { name: /save fields/i }));

    await waitFor(() =>
      expect(
        requests.some((request) => {
          if (request.method !== "PATCH" || request.url !== "/api/records/101/") {
            return false;
          }

          return JSON.stringify(JSON.parse(request.body?.toString() ?? "{}")) ===
            JSON.stringify({
              data: {
                commercial_name: "Clear Film 820",
                resin_family: "Nylon",
                melt_flow_index: 18.4,
                flame_retardant: true,
                approved_additives: ["Impact Modifier", "Color Masterbatch"]
              }
            });
        })
      ).toBe(true)
    );
    expect(requests.some((request) => request.url === "/api/documents/?record=101")).toBe(false);

    const uploadedFile = new File(["resin process notes"], "Process notes.pdf", {
      type: "application/pdf"
    });
    await user.upload(screen.getByLabelText(/upload document/i), uploadedFile);

    await waitFor(() => {
      const uploadRequest = requests.find(
        (request) => request.method === "POST" && request.url === "/api/documents/"
      );
      expect(uploadRequest?.body).toBeInstanceOf(FormData);
      const formData = uploadRequest?.body as FormData;
      expect(formData.get("file")).toBe(uploadedFile);
      expect(formData.get("owner_record")).toBe("101");
      expect(formData.get("title")).toBe("Process notes.pdf");
      expect(formData.get("document_type")).toBe("specification");
      expect(formData.get("revision_label")).toBe("A");
      expect(uploadRequest?.headers).toBeUndefined();
    });

    await user.click(screen.getByRole("button", { name: /release revision a/i }));
    await waitFor(() =>
      expect(
        requests.some(
          (request) =>
            request.method === "POST" &&
            request.url === "/api/documents/201/revisions/1/release/"
        )
      ).toBe(true)
    );

    await user.click(screen.getByRole("button", { name: /submit for review/i }));
    await waitFor(() =>
      expect(
        requests.some(
          (request) =>
            request.method === "POST" &&
            request.url === "/api/records/101/workflow/request_approval/"
        )
      ).toBe(true)
    );

    await user.click(screen.getByRole("button", { name: /accept change/i }));
    await waitFor(() =>
      expect(
        requests.some(
          (request) =>
            request.method === "POST" && request.url === "/api/folder-events/8/accept/"
        )
      ).toBe(true)
    );

    await user.click(screen.getByRole("button", { name: /ignore change/i }));
    await waitFor(() =>
      expect(
        requests.some(
          (request) =>
            request.method === "POST" && request.url === "/api/folder-events/8/ignore/"
        )
      ).toBe(true)
    );
  });
});

