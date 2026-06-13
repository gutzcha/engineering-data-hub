/*
 * ===
 * File Summary
 * Path: frontend\src\features\records\RecordCreate.test.tsx
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

import { RecordCreate } from "./RecordCreate";

const activeConfiguration = {
  data: {
    object_types: [
      {
        key: "product",
        label: "Product",
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
    ],
    form_layouts: [
      {
        key: "product_default",
        object_type_key: "product",
        sections: [{ label: "Identity", fields: ["commercial_name", "resin_family"] }]
      }
    ]
  }
};

function renderRecordCreate(initialEntries = ["/records/new"]) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } }
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={initialEntries}>
        <Routes>
          <Route path="/records/new" element={<RecordCreate />} />
          <Route path="/records/:recordId" element={<h1>Created record</h1>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("RecordCreate", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("creates a configured record and navigates to its detail page", async () => {
    const requests: Array<{ body?: BodyInit | null; method: string; url: string }> = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = input.toString();
        const method = init?.method ?? "GET";
        requests.push({ body: init?.body, method, url });

        if (url === "/api/config/active/") {
          return Response.json(activeConfiguration);
        }

        if (url === "/api/records/" && method === "POST") {
          return Response.json(
            {
              id: "record-101",
              object_type_key: "product",
              code: "PROD-000101",
              title: "Clear Film 900"
            },
            { status: 201 }
          );
        }

        return Response.json({ detail: `Unexpected request ${method} ${url}` }, { status: 500 });
      })
    );

    const user = userEvent.setup();
    renderRecordCreate();

    expect(await screen.findByRole("heading", { name: /new record/i })).toBeInTheDocument();
    await user.type(await screen.findByLabelText(/commercial name/i), "Clear Film 900");
    await user.selectOptions(screen.getByLabelText(/resin family/i), "PP");
    await user.click(screen.getByRole("button", { name: /create record/i }));

    await waitFor(() =>
      expect(
        requests.some((request) => {
          if (request.method !== "POST" || request.url !== "/api/records/") {
            return false;
          }

          return JSON.stringify(JSON.parse(request.body?.toString() ?? "{}")) ===
            JSON.stringify({
              object_type_key: "product",
              data: {
                commercial_name: "Clear Film 900",
                resin_family: "PP"
              }
            });
        })
      ).toBe(true)
    );
    expect(await screen.findByRole("heading", { name: /created record/i })).toBeInTheDocument();
  });

  it("respects query object type and posts that object_type_key", async () => {
    const requests: Array<{ body?: BodyInit | null; method: string; url: string }> = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = input.toString();
        const method = init?.method ?? "GET";
        requests.push({ body: init?.body, method, url });

        if (url === "/api/config/active/") {
          return Response.json({
            data: {
              object_types: [
                {
                  key: "product",
                  label: "Product",
                  title_field: "commercial_name",
                  fields: [{ key: "commercial_name", label: "Commercial Name", type: "text", required: true }]
                },
                {
                  key: "raw_material",
                  label: "Raw Material",
                  title_field: "material_name",
                  fields: [
                    {
                      key: "material_name",
                      label: "Material Name",
                      type: "text",
                      required: true
                    },
                    {
                      key: "form",
                      label: "Form",
                      type: "choice",
                      options: ["pellet", "powder"]
                    }
                  ]
                }
              ],
              form_layouts: []
            }
          });
        }

        if (url === "/api/records/" && method === "POST") {
          return Response.json(
            { id: "record-102", object_type_key: "raw_material", code: "MAT-000102", title: "HDPE Resin" },
            { status: 201 }
          );
        }

        return Response.json({ detail: `Unexpected request ${method} ${url}` }, { status: 500 });
      })
    );

    const user = userEvent.setup();
    renderRecordCreate(["/records/new?object_type_key=raw_material"]);

    expect(await screen.findByLabelText(/object type/i)).toHaveValue("raw_material");
    const materialNameInput = await screen.findByLabelText(/material name/i);
    await user.clear(materialNameInput);
    await user.type(materialNameInput, "HDPE Resin");
    await user.click(screen.getByRole("button", { name: /create record/i }));

    await waitFor(() => expect(screen.queryByRole("alert")).not.toBeInTheDocument());

    expect(
      requests.some((request) => {
        if (request.method !== "POST" || request.url !== "/api/records/") {
          return false;
        }

        const payload = JSON.parse(request.body?.toString() ?? "{}");
        return (
          payload.object_type_key === "raw_material" &&
          payload.data?.material_name === "HDPE Resin"
        );
      })
    ).toBe(true);
  });
});

