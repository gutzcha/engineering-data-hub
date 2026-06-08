import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ConfigWorkspace } from "./ConfigWorkspace";

const activeConfiguration = {
  id: 1,
  version: 7,
  published_at: "2026-06-06T09:30:00Z",
  published_by: 2,
  data: {
    object_types: [
      {
        key: "product",
        label: "Product",
        plural_label: "Products",
        code_pattern: "PROD-{seq:000000}",
        title_field: "commercial_name",
        folder_template_key: "product_standard",
        default_workflow_key: "engineering_release",
        fields: [
          {
            key: "commercial_name",
            label: "Commercial Name",
            type: "text",
            required: true,
            searchable: true,
            unique: true
          },
          {
            key: "resin_family",
            label: "Resin Family",
            type: "choice",
            required: false,
            searchable: true,
            unique: false,
            options: ["PP", "HDPE"]
          },
          {
            key: "supplier",
            label: "Supplier",
            type: "record_ref",
            required: false,
            reference_target_type: "supplier"
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
            label: "Quality",
            fields: ["supplier"]
          }
        ]
      }
    ],
    folder_templates: [
      {
        key: "product_standard",
        label: "Product Standard",
        pattern: "/Products/{code}-{commercial_name}/Release"
      }
    ],
    workflows: [
      {
        key: "engineering_release",
        label: "Engineering Release",
        states: ["draft", "review", "released"],
        transitions: [
          {
            from: "draft",
            to: "review",
            guard: "required_fields_complete",
            task_template: "Engineering review"
          }
        ],
        release_rules: ["quality_approval_required"]
      }
    ],
    relationship_types: [],
    dashboards: []
  }
};

const historyConfigurations = [
  activeConfiguration,
  {
    ...activeConfiguration,
    id: 0,
    version: 6,
    published_at: "2026-06-05T10:00:00Z"
  }
];

function renderWorkspace() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } }
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <ConfigWorkspace />
    </QueryClientProvider>
  );
}

describe("ConfigWorkspace", () => {
  beforeEach(() => {
    vi.useRealTimers();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("validates a draft before enabling publish and then records the published version", async () => {
    const requests: Array<{ body?: unknown; method: string; url: string }> = [];
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = input.toString();
      requests.push({
        body: init?.body ? JSON.parse(init.body.toString()) : undefined,
        method: init?.method ?? "GET",
        url
      });

      if (url === "/api/config/active/" && (init?.method ?? "GET") === "GET") {
        return Response.json(activeConfiguration);
      }

      if (url === "/api/config/history/" && (init?.method ?? "GET") === "GET") {
        return Response.json(historyConfigurations);
      }

      if (url === "/api/config/drafts/" && init?.method === "POST") {
        return Response.json(
          {
            id: 41,
            status: "draft",
            data: activeConfiguration.data,
            created_at: "2026-06-07T08:00:00Z",
            updated_at: "2026-06-07T08:00:00Z"
          },
          { status: 201 }
        );
      }

      if (url === "/api/config/drafts/41/" && init?.method === "PATCH") {
        return Response.json({
          id: 41,
          status: "draft",
          data: JSON.parse(init.body?.toString() ?? "{}").data,
          updated_at: "2026-06-07T08:05:00Z"
        });
      }

      if (url === "/api/config/drafts/41/validate/" && init?.method === "POST") {
        return Response.json({ errors: [] });
      }

      if (url === "/api/config/drafts/41/publish/" && init?.method === "POST") {
        return Response.json(
          {
            ...activeConfiguration,
            id: 2,
            version: 8,
            published_at: "2026-06-07T09:15:00Z"
          },
          { status: 201 }
        );
      }

      return Response.json({ detail: "Unexpected request" }, { status: 500 });
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    renderWorkspace();

    expect(
      await screen.findByRole("heading", { name: /admin configuration/i })
    ).toBeInTheDocument();
    expect(await screen.findAllByText(/published v7/i)).not.toHaveLength(0);
    expect(
      screen.getByRole("button", { name: /publish configuration/i })
    ).toBeDisabled();
    await user.click(screen.getByRole("tab", { name: /history/i }));
    expect(screen.getByRole("list", { name: /publish history/i })).toHaveTextContent(
      /v6/i
    );

    await user.click(screen.getByRole("button", { name: /create draft/i }));
    await user.clear(screen.getByLabelText(/object key/i));
    await user.type(screen.getByLabelText(/object key/i), "finished_product");

    expect(screen.getByDisplayValue("finished_product")).toBeInTheDocument();
    expect(screen.getByLabelText(/commercial name required/i)).toBeChecked();
    expect(screen.getByLabelText(/commercial name searchable/i)).toBeChecked();
    expect(screen.getByLabelText(/commercial name unique/i)).toBeChecked();
    expect(screen.getByLabelText(/resin family choice options/i)).toHaveValue(
      "PP, HDPE"
    );
    expect(screen.getByLabelText(/supplier reference target type/i)).toHaveValue(
      "supplier"
    );
    expect(screen.getByText("/Products/PROD-000123-Clear Film/Release")).toBeInTheDocument();
    expect(screen.getByLabelText(/states/i)).toHaveValue("draft, review, released");
    expect(screen.getByLabelText(/task templates/i)).toHaveValue(
      "Engineering review"
    );
    expect(screen.getByLabelText(/release rules/i)).toHaveValue(
      "quality_approval_required"
    );
    await user.clear(screen.getByLabelText(/section label/i));
    await user.type(screen.getByLabelText(/section label/i), "Product Identity");
    fireEvent.change(screen.getByLabelText(/visible fields/i), {
      target: { value: "commercial_name, supplier" }
    });

    await user.click(screen.getByRole("button", { name: /add transition/i }));
    await user.selectOptions(screen.getByLabelText(/selected transition/i), "1");
    await user.clear(screen.getByLabelText(/transition from/i));
    await user.type(screen.getByLabelText(/transition from/i), "review");
    await user.clear(screen.getByLabelText(/transition to/i));
    await user.type(screen.getByLabelText(/transition to/i), "released");
    await user.clear(screen.getByLabelText(/guards/i));
    await user.type(screen.getByLabelText(/guards/i), "quality_approved");
    await user.clear(screen.getByLabelText(/task templates/i));
    await user.type(screen.getByLabelText(/task templates/i), "Release signoff");

    await user.click(screen.getByRole("button", { name: /validate draft/i }));

    expect(await screen.findAllByText(/no validation errors/i)).not.toHaveLength(0);
    expect(
      screen.getByRole("button", { name: /publish configuration/i })
    ).toBeEnabled();

    await user.click(screen.getByRole("button", { name: /publish configuration/i }));

    await waitFor(() =>
      expect(screen.getByText(/published v8/i)).toBeInTheDocument()
    );
    expect(within(screen.getByRole("list", { name: /publish history/i })).getByText(/v8/i)).toBeInTheDocument();
    const validateIndex = requests.findIndex(
      (request) => request.url === "/api/config/drafts/41/validate/"
    );
    const publishIndex = requests.findIndex(
      (request) => request.url === "/api/config/drafts/41/publish/"
    );
    const patchRequests = requests.filter(
      (request) => request.url === "/api/config/drafts/41/"
    );
    expect(patchRequests).toHaveLength(2);
    expect(requests.indexOf(patchRequests[0])).toBeLessThan(validateIndex);
    expect(requests.indexOf(patchRequests[1])).toBeLessThan(publishIndex);
    expect(requests.indexOf(patchRequests[1])).toBeGreaterThan(validateIndex);
    for (const patchRequest of patchRequests) {
      const patchedData = (patchRequest.body as { data: typeof activeConfiguration.data }).data;
      expect(patchedData.object_types[0].key).toBe("finished_product");
      expect(patchedData.form_layouts[0].sections).toEqual([
        {
          label: "Product Identity",
          fields: ["commercial_name", "supplier"]
        },
        {
          label: "Quality",
          fields: ["supplier"]
        }
      ]);
      expect(patchedData.workflows[0].transitions).toEqual([
        {
          from: "draft",
          to: "review",
          guard: "required_fields_complete",
          task_template: "Engineering review"
        },
        {
          from: "review",
          to: "released",
          guard: "quality_approved",
          task_template: "Release signoff"
        }
      ]);
    }
    expect(requests.map(({ method, url }) => ({ method, url }))).toEqual([
      { method: "GET", url: "/api/config/active/" },
      { method: "GET", url: "/api/config/history/" },
      { method: "POST", url: "/api/config/drafts/" },
      { method: "PATCH", url: "/api/config/drafts/41/" },
      { method: "POST", url: "/api/config/drafts/41/validate/" },
      { method: "PATCH", url: "/api/config/drafts/41/" },
      { method: "POST", url: "/api/config/drafts/41/publish/" }
    ]);
  });

  it("keeps publish disabled when validation reports errors", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = input.toString();

        if (url === "/api/config/active/") {
          return Response.json(activeConfiguration);
        }

        if (url === "/api/config/history/") {
          return Response.json(historyConfigurations);
        }

        if (url === "/api/config/drafts/" && init?.method === "POST") {
          return Response.json({ id: 42, status: "draft", data: activeConfiguration.data }, { status: 201 });
        }

        if (url === "/api/config/drafts/42/" && init?.method === "PATCH") {
          return Response.json({ id: 42, status: "draft", data: JSON.parse(init.body?.toString() ?? "{}").data });
        }

        if (url === "/api/config/drafts/42/validate/" && init?.method === "POST") {
          return Response.json({
            errors: [
              {
                path: "object_types[0].key",
                code: "invalid_object_type_key",
                message: "Object type keys must use lowercase snake case."
              }
            ]
          });
        }

        return Response.json({ detail: "Unexpected request" }, { status: 500 });
      })
    );
    const user = userEvent.setup();

    renderWorkspace();

    await screen.findAllByText(/published v7/i);
    await user.click(screen.getByRole("button", { name: /create draft/i }));
    await user.click(screen.getByRole("button", { name: /validate draft/i }));

    expect(
      await screen.findByText(/object type keys must use lowercase snake case/i)
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /publish configuration/i })
    ).toBeDisabled();
  });

  it("requires confirmation before publishing breaking schema changes", async () => {
    const requests: Array<{ body?: unknown; method: string; url: string }> = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = input.toString();
        requests.push({
          body: init?.body ? JSON.parse(init.body.toString()) : undefined,
          method: init?.method ?? "GET",
          url
        });

        if (url === "/api/config/active/") {
          return Response.json(activeConfiguration);
        }

        if (url === "/api/config/history/") {
          return Response.json(historyConfigurations);
        }

        if (url === "/api/config/drafts/" && init?.method === "POST") {
          return Response.json(
            { id: 44, status: "draft", data: activeConfiguration.data },
            { status: 201 }
          );
        }

        if (url === "/api/config/drafts/44/" && init?.method === "PATCH") {
          return Response.json({
            id: 44,
            status: "draft",
            data: JSON.parse(init.body?.toString() ?? "{}").data
          });
        }

        if (url === "/api/config/drafts/44/validate/" && init?.method === "POST") {
          return Response.json({
            errors: [],
            breaking_changes: [
              {
                path: "object_types.raw_material.fields.material_family",
                code: "field_removed",
                message:
                  "Field 'Material Family' (material_family) was removed from Raw Material. Existing values stay in record data but will no longer appear in normal forms."
              }
            ]
          });
        }

        if (url === "/api/config/drafts/44/publish/" && init?.method === "POST") {
          return Response.json(
            {
              ...activeConfiguration,
              id: 3,
              version: 8,
              published_at: "2026-06-07T10:15:00Z"
            },
            { status: 201 }
          );
        }

        return Response.json({ detail: "Unexpected request" }, { status: 500 });
      })
    );
    const user = userEvent.setup();

    renderWorkspace();

    await screen.findAllByText(/published v7/i);
    await user.click(screen.getByRole("button", { name: /create draft/i }));
    await user.click(screen.getByRole("button", { name: /validate draft/i }));

    expect(await screen.findByText(/material family.*removed/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /publish configuration/i })
    ).toBeDisabled();

    await user.click(screen.getByRole("tab", { name: /publish/i }));
    const publishPanel = screen
      .getByRole("heading", { name: /release configuration/i })
      .closest("section") as HTMLElement;
    const confirmation = within(publishPanel).getByRole("checkbox", {
      name: /i understand this can hide or invalidate existing record data/i
    });
    const publishButton = within(publishPanel).getByRole("button", {
      name: /publish configuration/i
    });

    expect(confirmation).not.toBeChecked();
    expect(publishButton).toBeDisabled();

    await user.click(confirmation);
    expect(publishButton).toBeEnabled();
    await user.click(publishButton);

    await waitFor(() => expect(screen.getByText(/published v8/i)).toBeInTheDocument());
    const publishRequest = requests.find(
      (request) => request.url === "/api/config/drafts/44/publish/"
    );
    expect(publishRequest?.body).toEqual({ confirm_breaking_changes: true });
  });

  it("clears validation success after a later draft persistence failure", async () => {
    let patchCount = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = input.toString();

        if (url === "/api/config/active/") {
          return Response.json(activeConfiguration);
        }

        if (url === "/api/config/history/") {
          return Response.json(historyConfigurations);
        }

        if (url === "/api/config/drafts/" && init?.method === "POST") {
          return Response.json(
            { id: 43, status: "draft", data: activeConfiguration.data },
            { status: 201 }
          );
        }

        if (url === "/api/config/drafts/43/" && init?.method === "PATCH") {
          patchCount += 1;
          if (patchCount === 1) {
            return Response.json({
              id: 43,
              status: "draft",
              data: JSON.parse(init.body?.toString() ?? "{}").data
            });
          }

          return Response.json(
            { detail: "Only draft configurations can be updated." },
            { status: 400, statusText: "Bad Request" }
          );
        }

        if (url === "/api/config/drafts/43/validate/" && init?.method === "POST") {
          return Response.json({ errors: [] });
        }

        return Response.json({ detail: "Unexpected request" }, { status: 500 });
      })
    );
    const user = userEvent.setup();

    renderWorkspace();

    await screen.findAllByText(/published v7/i);
    await user.click(screen.getByRole("button", { name: /create draft/i }));
    await user.click(screen.getByRole("button", { name: /validate draft/i }));

    expect(await screen.findAllByText(/no validation errors/i)).not.toHaveLength(0);
    expect(
      screen.getByRole("button", { name: /publish configuration/i })
    ).toBeEnabled();

    await user.click(screen.getByRole("button", { name: /validate draft/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /only draft configurations can be updated/i
    );
    expect(
      screen.getByRole("button", { name: /publish configuration/i })
    ).toBeDisabled();
  });
});
