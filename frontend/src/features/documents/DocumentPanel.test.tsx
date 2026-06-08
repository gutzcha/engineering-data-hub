import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DocumentDetailPage, DocumentPanel } from "./DocumentPanel";

describe("DocumentPanel", () => {
  afterEach(() => {
    cleanup();
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

  it("shows the full revision history when current and draft revisions exist", () => {
    render(
      <MemoryRouter>
        <DocumentPanel
          documents={[
            {
              id: 77,
              title: "PC technical data sheet",
              current_revision: {
                id: 5,
                revision_label: "A",
                extraction_status: "extracted",
                state: "released"
              },
              revisions: [
                {
                  id: 5,
                  revision_label: "A",
                  extraction_status: "extracted",
                  state: "released"
                },
                {
                  id: 6,
                  revision_label: "B",
                  extraction_status: "extracted",
                  state: "draft"
                }
              ]
            }
          ]}
        />
      </MemoryRouter>
    );

    const documentItem = screen.getByText("PC technical data sheet").closest("article");
    expect(documentItem).not.toBeNull();
    const revisionHistory = within(documentItem as HTMLElement).getByLabelText("Revision history");
    expect(revisionHistory).toHaveTextContent(/vA/i);
    expect(revisionHistory).toHaveTextContent(/vB/i);
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
      const documentLink = screen
        .getAllByText("PC technical data sheet")
        .find((element) => element.tagName === "A");
      const documentItem = documentLink?.closest("article");
      expect(documentItem).not.toBeNull();
      expect(within(documentItem as HTMLElement).getByLabelText("Revision history")).toHaveTextContent(/vB/i);
    });
    await waitFor(() => {
      expect(requests).toContainEqual({
        method: "POST",
        url: "/api/documents/77/revisions/"
      });
    });
  });

  it("archives a controlled document from the detail page without deleting it", async () => {
    const user = userEvent.setup();
    const requests: Array<{ method: string; url: string }> = [];
    stubDocumentFetch(requests);

    renderDocumentRoute("/documents/77");

    await user.click(await screen.findByRole("button", { name: /archive document/i }));

    expect(await screen.findByRole("status")).toHaveTextContent(/document archived/i);
    const documentLink = screen.getByRole("link", { name: /pc technical data sheet/i });
    expect(documentLink.closest("article")).toHaveTextContent(/obsolete/i);
    expect(requests).toContainEqual({
      method: "POST",
      url: "/api/documents/77/archive/"
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
  let uploadedRevision: {
    id: number;
    revision_label: string;
    file_name: string;
    extraction_status: string;
    state: string;
  } | null = null;
  let archived = false;

  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();
      const method = init?.method ?? "GET";
      requests.push({ method, url });

      if (url === "/api/documents/77/" && method === "GET") {
        const currentRevision = {
          id: 5,
          revision_label: "A",
          file_name: "pc.pdf",
          extraction_status: "extracted",
          state: "draft",
          created_at: "2026-06-08T08:00:00Z"
        };
        return jsonResponse({
          id: 77,
          title: "PC technical data sheet",
          document_type: "technical_data_sheet",
          state: archived ? "obsolete" : "draft",
          current_revision: currentRevision,
          revisions: uploadedRevision ? [currentRevision, uploadedRevision] : [currentRevision]
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
        uploadedRevision = {
          id: 6,
          revision_label: "B",
          file_name: "pc-revision-b.pdf",
          extraction_status: "extracted",
          state: "draft"
        };
        return jsonResponse(uploadedRevision, 201);
      }

      if (url === "/api/documents/77/archive/" && method === "POST") {
        archived = true;
        return jsonResponse({
          id: 77,
          title: "PC technical data sheet",
          document_type: "technical_data_sheet",
          state: "obsolete",
          current_revision: {
            id: 5,
            revision_label: "A",
            file_name: "pc.pdf",
            extraction_status: "extracted",
            state: "draft"
          },
          revisions: []
        });
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
