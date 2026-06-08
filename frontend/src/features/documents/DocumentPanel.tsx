import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Archive, Download, Eye, FileText, FileUp, Link as LinkIcon, Rocket } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { StatusBadge } from "../../components/StatusBadge";
import { apiGet, apiPost, apiPostForm } from "../../lib/api";

export type DocumentRevision = {
  id?: string | number;
  revision_label?: string;
  version?: string | number;
  file_name?: string;
  state?: string;
  extraction_status?: string;
  created_at?: string;
  released_at?: string;
};

export type DocumentItem = {
  id: string | number;
  title?: string;
  name?: string;
  filename?: string;
  status?: string;
  state?: string;
  document_type?: string;
  extraction_status?: string;
  preview_url?: string;
  download_url?: string;
  audit_url?: string;
  current_revision?: DocumentRevision | null;
  revisions?: DocumentRevision[];
};

type DocumentPreview = {
  document: string | number;
  revision: string | number;
  revision_label?: string;
  file_name?: string;
  mime_type?: string;
  extraction_status?: string;
  extracted_text?: string;
  truncated?: boolean;
};

type DocumentAuditEvent = {
  id: string | number;
  actor?: string | number | null;
  actor_username?: string | null;
  action: string;
  object_type?: string;
  object_id?: string;
  before?: Record<string, unknown> | null;
  after?: Record<string, unknown> | null;
  created_at?: string;
};

type AuditResponse = {
  results?: DocumentAuditEvent[];
};

export type DocumentUploadMetadata = {
  owner_record?: string | number;
  title?: string;
  document_type?: string;
  revision_label?: string;
};

type DocumentPanelProps = {
  documents?: DocumentItem[];
  emptyMessage?: string;
  isUploading?: boolean;
  ownerRecordId?: string | number;
  onUpload?: (file: File, metadata: DocumentUploadMetadata) => void;
  onRelease?: (documentId: string | number, revisionId: string | number) => void;
  onArchive?: (documentId: string | number) => void;
};

export function DocumentPanel({
  documents = [],
  emptyMessage = "No documents are attached to this record.",
  isUploading = false,
  ownerRecordId,
  onUpload,
  onRelease,
  onArchive
}: DocumentPanelProps) {
  const [selectedFileName, setSelectedFileName] = useState("");
  const [documentType, setDocumentType] = useState("specification");
  const [revisionLabel, setRevisionLabel] = useState("A");

  return (
    <section className="table-panel detail-panel" aria-labelledby="document-panel-title">
      <div className="panel-heading">
        <div>
          <p className="section-kicker">Controlled files</p>
          <h2 id="document-panel-title">Documents</h2>
        </div>
        <StatusBadge tone={documents.length ? "active" : "neutral"}>
          {documents.length} Files
        </StatusBadge>
      </div>
      <div className="record-panel-body">
        {ownerRecordId && onUpload && (
          <div className="admin-form-grid">
            <label className="field-control">
              <span>Document Type</span>
              <input
                aria-label="Document type"
                value={documentType}
                onChange={(event) => setDocumentType(event.target.value)}
              />
            </label>
            <label className="field-control">
              <span>Revision Label</span>
              <input
                aria-label="Revision label"
                value={revisionLabel}
                onChange={(event) => setRevisionLabel(event.target.value)}
              />
            </label>
          </div>
        )}
        {onUpload && (
          <label className="upload-control">
            <FileUp aria-hidden="true" size={16} />
            <span>{isUploading ? "Uploading" : selectedFileName || "Upload document"}</span>
            <input
              aria-label="Upload document"
              type="file"
              disabled={isUploading || !ownerRecordId}
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) {
                  setSelectedFileName(file.name);
                  onUpload(file, {
                    owner_record: ownerRecordId,
                    title: file.name,
                    document_type: documentType,
                    revision_label: revisionLabel
                  });
                }
              }}
            />
          </label>
        )}
        <div className="document-list" role="list" aria-label="Documents">
          {documents.length === 0 ? (
            <p className="admin-muted">{emptyMessage}</p>
          ) : (
            documents.map((document) => (
              <DocumentListItem
                document={document}
                key={document.id}
                onArchive={onArchive}
                onRelease={onRelease}
              />
            ))
          )}
        </div>
      </div>
    </section>
  );
}

export function DocumentLibraryPage() {
  const queryClient = useQueryClient();
  const [ownerRecord, setOwnerRecord] = useState("");
  const documentsQuery = useQuery({
    queryKey: ["documents"],
    queryFn: () => apiGet<DocumentItem[]>("/documents/")
  });
  const uploadDocument = useMutation({
    mutationFn: ({
      file,
      metadata
    }: {
      file: File;
      metadata: DocumentUploadMetadata;
    }) =>
      apiPostForm<DocumentItem>(
        "/documents/",
        buildDocumentUploadForm(file, { ...metadata, owner_record: ownerRecord })
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["documents"] });
    }
  });

  return (
    <div className="page-stack">
      <section className="workspace-header" aria-labelledby="documents-title">
        <div>
          <p className="section-kicker">Specifications and controlled files</p>
          <h1 id="documents-title">Documents</h1>
        </div>
      </section>
      <section className="table-panel detail-panel" aria-labelledby="document-upload-title">
        <div className="panel-heading">
          <div>
            <p className="section-kicker">Create controlled document</p>
            <h2 id="document-upload-title">Document Library</h2>
          </div>
          <StatusBadge tone={documentsQuery.data?.length ? "active" : "neutral"}>
            {documentsQuery.isLoading ? "Loading" : `${documentsQuery.data?.length ?? 0} Files`}
          </StatusBadge>
        </div>
        <div className="record-panel-body">
          <label className="field-control">
            <span>Owner Record</span>
            <input
              aria-label="Owner record"
              value={ownerRecord}
              onChange={(event) => setOwnerRecord(event.target.value)}
            />
          </label>
          {documentsQuery.isError && (
            <p className="form-error">
              {documentsQuery.error instanceof Error
                ? documentsQuery.error.message
                : "Unable to load documents."}
            </p>
          )}
          <DocumentPanel
            documents={documentsQuery.data ?? []}
            emptyMessage={
              documentsQuery.isLoading
                ? "Loading controlled documents."
                : "No controlled documents are available."
            }
            ownerRecordId={ownerRecord}
            isUploading={uploadDocument.isPending}
            onUpload={(file, metadata) => uploadDocument.mutate({ file, metadata })}
          />
        </div>
      </section>
    </div>
  );
}

export function DocumentDetailPage() {
  const { documentId = "" } = useParams();
  const [searchParams] = useSearchParams();
  const queryClient = useQueryClient();
  const activeView = searchParams.get("view") ?? "overview";
  const [revisionLabel, setRevisionLabel] = useState("");
  const [revisionFile, setRevisionFile] = useState<File | null>(null);
  const [revisionNotice, setRevisionNotice] = useState("");
  const [archiveNotice, setArchiveNotice] = useState("");
  const documentQuery = useQuery({
    queryKey: ["document", documentId],
    queryFn: () => apiGet<DocumentItem>(`/documents/${documentId}/`),
    enabled: documentId.length > 0
  });
  const previewQuery = useQuery({
    queryKey: ["document", documentId, "preview"],
    queryFn: () => apiGet<DocumentPreview>(`/documents/${documentId}/preview/`),
    enabled: documentId.length > 0 && activeView === "preview"
  });
  const auditQuery = useQuery({
    queryKey: ["document", documentId, "audit"],
    queryFn: () => apiGet<AuditResponse>(`/documents/${documentId}/audit/`),
    enabled: documentId.length > 0 && activeView === "audit"
  });
  const addRevision = useMutation({
    mutationFn: ({ file, label }: { file: File; label: string }) =>
      apiPostForm<DocumentRevision>(
        `/documents/${documentId}/revisions/`,
        buildDocumentRevisionForm(file, label)
      ),
    onSuccess: (revision) => {
      setRevisionFile(null);
      setRevisionLabel("");
      setRevisionNotice(
        `Revision ${revision.revision_label ?? revision.version ?? revision.id ?? ""} uploaded.`.trim()
      );
      queryClient.setQueryData<DocumentItem | undefined>(
        ["document", documentId],
        (current) => (current ? documentWithRevision(current, revision) : current)
      );
      void queryClient.invalidateQueries({ queryKey: ["document", documentId] });
      void queryClient.invalidateQueries({ queryKey: ["documents"] });
    }
  });
  const archiveDocument = useMutation({
    mutationFn: () => apiPost<DocumentItem>(`/documents/${documentId}/archive/`, {}),
    onSuccess: (updatedDocument) => {
      setArchiveNotice("Document archived. It remains available for audit and history.");
      queryClient.setQueryData(["document", documentId], updatedDocument);
      void queryClient.invalidateQueries({ queryKey: ["documents"] });
      void queryClient.invalidateQueries({ queryKey: ["document", documentId, "audit"] });
    }
  });
  const document = documentQuery.data;

  function submitRevision(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const label = revisionLabel.trim();
    if (revisionFile && label) {
      addRevision.mutate({ file: revisionFile, label });
    }
  }

  return (
    <div className="page-stack">
      <section className="workspace-header" aria-labelledby="document-detail-title">
        <div>
          <p className="section-kicker">Controlled document</p>
          <h1 id="document-detail-title">{document?.title ?? `Document ${documentId}`}</h1>
        </div>
      </section>
      {documentQuery.isLoading ? (
        <section className="empty-state">
          <FileText aria-hidden="true" size={24} />
          <div>
            <h2>Loading document</h2>
          </div>
        </section>
      ) : documentQuery.isError || !document ? (
        <section className="empty-state">
          <FileText aria-hidden="true" size={24} />
          <div>
            <h2>Document unavailable</h2>
            <p>
              {documentQuery.error instanceof Error
                ? documentQuery.error.message
                : "The document could not be loaded."}
            </p>
          </div>
        </section>
      ) : (
        <DocumentPanel
          documents={[document]}
          emptyMessage="Document metadata is unavailable."
          onArchive={() => archiveDocument.mutate()}
        />
      )}
      {document && (
        <>
          {archiveNotice && (
            <div className="validation-success" role="status">
              {archiveNotice}
            </div>
          )}
          {archiveDocument.error && (
            <div className="admin-alert" role="alert">
              <strong>Document archive failed</strong>
              <span>{errorMessage(archiveDocument.error)}</span>
            </div>
          )}
          <section className="filter-panel" aria-label="Document detail views">
            <div className="segmented-tabs" role="tablist" aria-label="Document views">
              <Link
                className={activeView === "overview" ? "segmented-tab segmented-tab-active" : "segmented-tab"}
                to={`/documents/${document.id}`}
                role="tab"
                aria-selected={activeView === "overview"}
              >
                Overview
              </Link>
              <Link
                className={activeView === "preview" ? "segmented-tab segmented-tab-active" : "segmented-tab"}
                to={`/documents/${document.id}?view=preview`}
                role="tab"
                aria-selected={activeView === "preview"}
              >
                Preview
              </Link>
              <Link
                className={activeView === "audit" ? "segmented-tab segmented-tab-active" : "segmented-tab"}
                to={`/documents/${document.id}?view=audit`}
                role="tab"
                aria-selected={activeView === "audit"}
              >
                Audit
              </Link>
              <a
                className="segmented-tab"
                href={document.download_url ?? `/api/documents/${document.id}/download/`}
              >
                Download
              </a>
            </div>
          </section>

          {activeView === "preview" && (
            <DocumentPreviewPanel
              preview={previewQuery.data}
              isLoading={previewQuery.isLoading}
              error={previewQuery.error}
            />
          )}
          {activeView === "audit" && (
            <DocumentAuditPanel
              events={auditQuery.data?.results ?? []}
              isLoading={auditQuery.isLoading}
              error={auditQuery.error}
            />
          )}
          {activeView === "overview" && (
            <AddRevisionPanel
              error={addRevision.error}
              file={revisionFile}
              isUploading={addRevision.isPending}
              notice={revisionNotice}
              onFileChange={(file) => {
                setRevisionNotice("");
                setRevisionFile(file);
              }}
              onLabelChange={(label) => {
                setRevisionNotice("");
                setRevisionLabel(label);
              }}
              onSubmit={submitRevision}
              revisionLabel={revisionLabel}
            />
          )}
        </>
      )}
    </div>
  );
}

export function buildDocumentUploadForm(file: File, metadata: DocumentUploadMetadata = {}) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("title", metadata.title ?? file.name);

  if (metadata.owner_record !== undefined) {
    formData.append("owner_record", String(metadata.owner_record));
  }

  if (metadata.document_type) {
    formData.append("document_type", metadata.document_type);
  }

  if (metadata.revision_label) {
    formData.append("revision_label", metadata.revision_label);
  }

  return formData;
}

export function buildDocumentRevisionForm(file: File, revisionLabel: string) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("revision_label", revisionLabel);
  return formData;
}

function DocumentListItem({
  document,
  onArchive,
  onRelease
}: {
  document: DocumentItem;
  onArchive?: (documentId: string | number) => void;
  onRelease?: (documentId: string | number, revisionId: string | number) => void;
}) {
  const revision = currentRevision(document);
  const status = document.state ?? document.status ?? "draft";

  return (
    <article className="document-item" role="listitem">
      <div className="document-main">
        <strong>
          <Link to={`/documents/${document.id}`}>
            {document.title ?? document.name ?? document.filename ?? document.id}
          </Link>
        </strong>
        <span>
          Extraction:{" "}
          {document.extraction_status ?? revision?.extraction_status ?? "not started"}
        </span>
      </div>
      <StatusBadge tone={status === "released" ? "ready" : "review"}>{status}</StatusBadge>
      <RevisionHistory revisions={revisionsForHistory(document)} />
      <div className="document-actions">
        <Link className="button button-secondary" to={`/documents/${document.id}`}>
          <FileText aria-hidden="true" size={16} />
          Open
        </Link>
        <Link
          className="button button-secondary"
          to={`/documents/${document.id}?view=preview`}
        >
          <Eye aria-hidden="true" size={16} />
          Preview
        </Link>
        <a
          className="button button-secondary"
          href={document.download_url ?? `/api/documents/${document.id}/download/`}
        >
          <Download aria-hidden="true" size={16} />
          Download
        </a>
        <button
          aria-label={`Release revision ${revision?.revision_label ?? revision?.version ?? ""}`.trim()}
          className="button button-primary"
          type="button"
          onClick={() => revision?.id && onRelease?.(document.id, revision.id)}
          disabled={!onRelease || !revision?.id || revision.state === "released"}
        >
          <Rocket aria-hidden="true" size={16} />
          Release
        </button>
        <button
          aria-label="Archive Document"
          className="button button-secondary"
          type="button"
          onClick={() => onArchive?.(document.id)}
          disabled={!onArchive || status === "obsolete"}
        >
          <Archive aria-hidden="true" size={16} />
          Archive
        </button>
        <Link
          className="button button-secondary"
          to={`/documents/${document.id}?view=audit`}
        >
          <LinkIcon aria-hidden="true" size={16} />
          Audit
        </Link>
      </div>
    </article>
  );
}

function DocumentPreviewPanel({
  error,
  isLoading,
  preview
}: {
  error: unknown;
  isLoading: boolean;
  preview?: DocumentPreview;
}) {
  const terms = materialTerms(preview?.extracted_text ?? "");

  return (
    <section className="table-panel detail-panel" aria-labelledby="document-preview-title">
      <div className="panel-heading">
        <div>
          <p className="section-kicker">Extracted content</p>
          <h2 id="document-preview-title">Document Preview</h2>
        </div>
        <StatusBadge tone={preview?.extraction_status === "extracted" ? "ready" : "neutral"}>
          {isLoading ? "Loading" : preview?.extraction_status ?? "Unavailable"}
        </StatusBadge>
      </div>
      <div className="record-panel-body">
        {error ? (
          <div className="admin-alert" role="alert">
            <strong>Preview failed</strong>
            <span>{errorMessage(error)}</span>
          </div>
        ) : isLoading ? (
          <p className="admin-muted">Loading document preview.</p>
        ) : preview ? (
          <>
            <div className="admin-status-row" aria-label="Document preview metadata">
              <div className="admin-stat">
                <span>Revision</span>
                <strong>{preview.revision_label ?? preview.revision}</strong>
              </div>
              <div className="admin-stat">
                <span>File</span>
                <strong>{preview.file_name ?? "Not recorded"}</strong>
              </div>
              <div className="admin-stat">
                <span>Material terms</span>
                <strong>{terms.length ? terms.join(", ") : "None detected"}</strong>
              </div>
            </div>
            {preview.truncated && (
              <p className="admin-muted">Preview is shortened to the first extracted text segment.</p>
            )}
            <pre className="document-preview-text">
              {preview.extracted_text?.trim() || "No extracted text is available for this revision."}
            </pre>
          </>
        ) : (
          <p className="admin-muted">No preview is available for this document.</p>
        )}
      </div>
    </section>
  );
}

function DocumentAuditPanel({
  error,
  events,
  isLoading
}: {
  error: unknown;
  events: DocumentAuditEvent[];
  isLoading: boolean;
}) {
  return (
    <section className="table-panel detail-panel" aria-labelledby="document-audit-title">
      <div className="panel-heading">
        <div>
          <p className="section-kicker">History</p>
          <h2 id="document-audit-title">Document Audit</h2>
        </div>
        <StatusBadge tone={events.length ? "active" : "neutral"}>
          {isLoading ? "Loading" : `${events.length} Events`}
        </StatusBadge>
      </div>
      <div className="record-panel-body event-list" role="list" aria-label="Document audit events">
        {error ? (
          <div className="admin-alert" role="alert">
            <strong>Audit failed</strong>
            <span>{errorMessage(error)}</span>
          </div>
        ) : isLoading ? (
          <p className="admin-muted">Loading document audit history.</p>
        ) : events.length ? (
          events.map((event) => (
            <article className="event-item" role="listitem" key={event.id}>
              <strong>{humanize(event.action)}</strong>
              <span>{event.actor_username ?? event.actor ?? "System"}</span>
              <span>{formatDate(event.created_at)}</span>
            </article>
          ))
        ) : (
          <p className="admin-muted">No audit events are recorded for this document.</p>
        )}
      </div>
    </section>
  );
}

function AddRevisionPanel({
  error,
  file,
  isUploading,
  notice,
  onFileChange,
  onLabelChange,
  onSubmit,
  revisionLabel
}: {
  error: unknown;
  file: File | null;
  isUploading: boolean;
  notice: string;
  onFileChange: (file: File | null) => void;
  onLabelChange: (label: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  revisionLabel: string;
}) {
  return (
    <section className="table-panel detail-panel" aria-labelledby="add-revision-title">
      <div className="panel-heading">
        <div>
          <p className="section-kicker">Controlled revision</p>
          <h2 id="add-revision-title">Add Revision</h2>
        </div>
        <FileUp aria-hidden="true" size={18} />
      </div>
      <form className="record-panel-body" onSubmit={onSubmit}>
        {notice && <div className="validation-success">{notice}</div>}
        {error ? (
          <div className="admin-alert" role="alert">
            <strong>Revision upload failed</strong>
            <span>{errorMessage(error)}</span>
          </div>
        ) : null}
        <div className="admin-form-grid">
          <label className="field-control">
            <span>Revision Label</span>
            <input
              aria-label="New revision label"
              value={revisionLabel}
              onChange={(event) => onLabelChange(event.target.value)}
            />
          </label>
          <label className="upload-control">
            <FileUp aria-hidden="true" size={16} />
            <span>{file?.name ?? "Choose revision file"}</span>
            <input
              aria-label="New revision file"
              type="file"
              onChange={(event) => onFileChange(event.target.files?.[0] ?? null)}
            />
          </label>
        </div>
        <button
          className="button button-primary"
          type="submit"
          disabled={isUploading || !file || !revisionLabel.trim()}
        >
          <FileUp aria-hidden="true" size={16} />
          {isUploading ? "Uploading" : "Add Revision"}
        </button>
      </form>
    </section>
  );
}

function RevisionHistory({ revisions }: { revisions: DocumentRevision[] }) {
  return (
    <div className="revision-list" aria-label="Revision history">
      {revisions.length === 0 ? (
        <span>No revisions</span>
      ) : (
        revisions.map((revision, index) => (
          <span key={revision.id ?? index}>
            v{revision.revision_label ?? revision.version ?? index + 1}{" "}
            {formatDate(revision.released_at ?? revision.created_at)}
          </span>
        ))
      )}
    </div>
  );
}

function currentRevision(document: DocumentItem) {
  return document.current_revision ?? document.revisions?.[0] ?? null;
}

function revisionsForHistory(document: DocumentItem) {
  if (document.revisions?.length) {
    return document.revisions;
  }
  const revision = currentRevision(document);
  return revision ? [revision] : [];
}

function documentWithRevision(document: DocumentItem, revision: DocumentRevision): DocumentItem {
  return {
    ...document,
    revisions: upsertRevision(revisionsForHistory(document), revision)
  };
}

function upsertRevision(revisions: DocumentRevision[], revision: DocumentRevision) {
  const revisionId = revision.id ? String(revision.id) : "";
  const revisionLabel = revision.revision_label ?? revision.version;
  const existingIndex = revisions.findIndex((existingRevision) => {
    if (revisionId && existingRevision.id && String(existingRevision.id) === revisionId) {
      return true;
    }
    return (
      revisionLabel !== undefined &&
      (existingRevision.revision_label ?? existingRevision.version) === revisionLabel
    );
  });

  if (existingIndex >= 0) {
    return revisions.map((existingRevision, index) =>
      index === existingIndex ? revision : existingRevision
    );
  }
  return [...revisions, revision];
}

function formatDate(value?: string) {
  if (!value) {
    return "";
  }

  return new Intl.DateTimeFormat("en", { dateStyle: "medium" }).format(new Date(value));
}

function materialTerms(text: string) {
  const normalized = text.toLowerCase();
  const terms = ["polycarbonate", "abs", "hdpe", "pvc", "polypropylene", "tensile", "density", "impact"];
  return terms.filter((term) => normalized.includes(term));
}

function humanize(value: string) {
  return value.replace(/[_-]+/g, " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Document request failed.";
}
