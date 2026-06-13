import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DocumentPanel } from "./DocumentPanel";

function renderPanel() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } }
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <DocumentPanel ownerRecordId="owner-101" />
    </QueryClientProvider>
  );
}

describe("DocumentPanel", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("posts owner-based upload metadata and selected metadata values", async () => {
    const onUpload = vi.fn();
    render(
      <QueryClientProvider
        client={
          new QueryClient({
            defaultOptions: { queries: { retry: false }, mutations: { retry: false } }
          })
        }
      >
        <DocumentPanel ownerRecordId="owner-101" onUpload={onUpload} />
      </QueryClientProvider>
    );
    const user = userEvent.setup();

    const documentType = await screen.findByLabelText("Document type");
    const revisionLabel = await screen.findByLabelText("Revision label");
    const uploadInput = screen.getByLabelText("Upload document");
    const file = new File(["polyolefin"], "pp-spec.pdf", { type: "application/pdf" });

    await user.clear(documentType);
    await user.type(documentType, "release spec");
    await user.clear(revisionLabel);
    await user.type(revisionLabel, "B");
    await user.upload(uploadInput, file);

    expect(onUpload).toHaveBeenCalledTimes(1);
    const uploadCall = onUpload.mock.calls[0];
    expect(uploadCall[1]).toEqual({
      owner_record: "owner-101",
      title: file.name,
      document_type: "release spec",
      revision_label: "B"
    });
  });

  it("disables upload while no owner record is selected", () => {
    renderPanel();
    expect(screen.getByLabelText("Upload document")).toBeDisabled();
  });
});
