import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DocumentDetailPage, DocumentPanel } from "./DocumentPanel";

describe("DocumentPanel", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("keeps preview and audit actions inside the React document detail UI", () => {
    render(
      <MemoryRouter>
        <DocumentPanel
          documents={[
            {
              id: 77,
              title: "PC technical data sheet",
              download_url: "/api/documents/77/download/",
              current_revision: {
                id: 5,
                revision_label: "A",
                extraction_status: "extracted"
              }
            }
          ]}
        />
      </MemoryRouter>
    );

    expect(screen.getByRole("link", { name: /^Open$/i })).toHaveAttribute(
      "href",
      "/documents/77"
    );
    expect(screen.getByRole("link", { name: /^Preview$/i })).toHaveAttribute(
      "href",
      "/documents/77?view=preview"
    );
    expect(screen.getByRole("link", { name: /^Audit$/i })).toHaveAttribute(
      "href",
      "/documents/77?view=audit"
    );
    expect(screen.getByRole("link", { name: /^Download$/i })).toHaveAttribute(
      "href",
      "/api/documents/77/download/"
    );
  });

  it("renders document preview as formatted UI instead of raw JSON", async () => {
    stubDocumentFetch();

    renderDocumentRoute("/documents/77?view=preview");

    expect(await screen.findByRole("heading", { name: "Document Preview" })).toBeInTheDocument();
    expect(screen.getAllByText(/polycarbonate.*tensile.*density/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Polycarbonate sheet tensile data/i)).toBeInTheDocument();
    expect(screen.queryByText(/"extracted_text"/i)).not.toBeInTheDocument();
  });

  it("renders document audit as formatted UI instead of raw JSON", async () => {
    stubDocumentFetch();

    renderDocumentRoute("/documents/77?view=audit");

    expect(await screen.findByRole("heading", { name: "Document Audit" })).toBeInTheDocument();
    expect(screen.getByText("Document Created")).toBeInTheDocument();
    expect(screen.getByText("qa_engineer")).toBeInTheDocument();
    expect(screen.queryByText(/"results"/i)).not.toBeInTheDocument();
  });

  it("uploads a new document revision from the detail page", async () => {
    const user = userEvent.setup();
    const requests: Array<{ method: string; url: string }> = [];
    stubDocumentFetch(requests);

    renderDocumentRoute("/documents/77");

    await user.type(await screen.findByLabelText(/new revision label/i), "B");
    await user.upload(
      screen.getByLabelText(/new revision file/i),
      new File(["revision b"], "pc-revision-b.pdf", { type: "application/pdf" })
    );
    await user.click(screen.getByRole("button", { name: /^Add Revision$/i }));

    expect(await screen.findByText("Revision B uploaded.")).toBeInTheDocument();
    await waitFor(() => {
      expect(requests).toContainEqual({
        method: "POST",
        url: "/api/documents/77/revisions/"
      });
    });
  });
});

function renderDocumentRoute(initialEntry: string) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } }
  });

  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route path="/documents/:documentId" element={<DocumentDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

function stubDocumentFetch(requests: Array<{ method: string; url: string }> = []) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();
      const method = init?.method ?? "GET";
      requests.push({ method, url });

      if (url === "/api/documents/77/" && method === "GET") {
        return jsonResponse({
          id: 77,
          title: "PC technical data sheet",
          document_type: "technical_data_sheet",
          state: "draft",
          current_revision: {
            id: 5,
            revision_label: "A",
            file_name: "pc.pdf",
            extraction_status: "extracted",
            state: "draft",
            created_at: "2026-06-08T08:00:00Z"
          }
        });
      }

      if (url === "/api/documents/77/preview/" && method === "GET") {
        return jsonResponse({
          document: 77,
          revision: 5,
          revision_label: "A",
          file_name: "pc.pdf",
          extraction_status: "extracted",
          extracted_text: "Polycarbonate sheet tensile data includes density and impact values.",
          truncated: false
        });
      }

      if (url === "/api/documents/77/audit/" && method === "GET") {
        return jsonResponse({
          results: [
            {
              id: 900,
              action: "document_created",
              actor_username: "qa_engineer",
              object_type: "document",
              object_id: "77",
              created_at: "2026-06-08T09:00:00Z"
            }
          ]
        });
      }

      if (url === "/api/documents/77/revisions/" && method === "POST") {
        return jsonResponse(
          {
            id: 6,
            revision_label: "B",
            file_name: "pc-revision-b.pdf",
            extraction_status: "extracted",
            state: "draft"
          },
          201
        );
      }

      if (url === "/api/documents/" && method === "GET") {
        return jsonResponse([]);
      }

      return jsonResponse({ detail: `Unhandled test URL ${method} ${url}` }, 404);
    })
  );
}

function jsonResponse(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" }
  });
}
