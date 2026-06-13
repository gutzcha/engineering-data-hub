/*
 * ===
 * File Summary
 * Path: frontend\src\features\documents\DocumentPanel.tsx
 * Type: typescript
 * Purpose: Frontend feature module implementing business flows and UI surfaces.
 * Primary responsibilities:
 * - Domain behavior is summarized for fast onboarding and avoids full-file reread.
 * - Core symbols: DocumentRevision, DocumentItem, DocumentUploadMetadata, DocumentPanel, DocumentLibraryPage
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

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, Eye, FileText, FileUp, Link as LinkIcon, Rocket } from "lucide-react";
import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

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
  owner_record?: string | number;
  owner_record_code?: string;
  owner_record_title?: string;
  owner_record_object_type?: string;
  current_revision?: DocumentRevision | null;
  revisions?: DocumentRevision[];
};

export type DocumentUploadMetadata = {
  owner_record?: string | number;
  title?: string;
  document_type?: string;
  revision_label?: string;
};

type DocumentListResponse = {
  count?: number;
  next?: string | null;
  previous?: string | null;
  results?: DocumentItem[];
};

type DocumentPanelProps = {
  documents?: DocumentItem[];
  isUploading?: boolean;
  ownerRecordId?: string | number;
  onUpload?: (file: File, metadata: DocumentUploadMetadata) => void;
  onRelease?: (documentId: string | number, revisionId: string | number) => void;
};

export function DocumentPanel({
  documents = [],
  isUploading = false,
  ownerRecordId,
  onUpload,
  onRelease
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
        {ownerRecordId && (
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
        <label className="upload-control">
          <FileUp aria-hidden="true" size={16} />
          <span>{isUploading ? "Uploading" : selectedFileName || "Upload document"}</span>
          <input
            aria-label="Upload document"
            type="file"
            disabled={!onUpload || isUploading || !ownerRecordId}
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) {
                setSelectedFileName(file.name);
                onUpload?.(file, {
                  owner_record: ownerRecordId,
                  title: file.name,
                  document_type: documentType,
                  revision_label: revisionLabel
                });
              }
            }}
          />
        </label>
        <div className="document-list" role="list" aria-label="Documents">
          {documents.length === 0 ? (
            <p className="admin-muted">No documents are attached to this record.</p>
          ) : (
            documents.map((document) => (
              <DocumentListItem
                document={document}
                key={document.id}
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
  const [documentType, setDocumentType] = useState("");
  const ownerFilter = ownerRecord.trim();
  const typeFilter = documentType.trim();

  const documentsQuery = useQuery({
    queryKey: ["documents", "list", ownerFilter, typeFilter],
    queryFn: () =>
      apiGet<DocumentItem[] | DocumentListResponse>(`/documents/${documentsQueryString(ownerFilter, typeFilter)}`)
  });

  const documents = useMemo(() => {
    const list = asDocumentList(documentsQuery.data);
    if (!typeFilter) {
      return list;
    }
    return list.filter(
      (document) =>
        (document.document_type ?? "").toLowerCase() === typeFilter.toLowerCase()
    );
  }, [documentsQuery.data, typeFilter]);

  const uploadDocument = useMutation({
    mutationFn: ({ file, metadata }: { file: File; metadata: DocumentUploadMetadata }) =>
      apiPostForm<DocumentItem>(
        "/documents/",
        buildDocumentUploadForm(file, {
          ...metadata,
          owner_record: ownerFilter || metadata.owner_record
        })
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["documents", "list"] });
    }
  });

  const releaseDocument = useMutation({
    mutationFn: ({ documentId, revisionId }: { documentId: string | number; revisionId: string | number }) =>
      apiPost<DocumentItem>(`/documents/${documentId}/revisions/${revisionId}/release/`, {}),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["documents", "list"] });
    }
  });

  const uploadError = uploadDocument.error ?? releaseDocument.error;

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
            <h2 id="document-upload-title">Upload to Owner Record</h2>
          </div>
          <StatusBadge tone={uploadDocument.isPending ? "neutral" : documentsQuery.isLoading ? "neutral" : "active"}>
            {documentsQuery.isLoading
              ? "Loading documents"
              : `${documents.length} Loaded`}
          </StatusBadge>
        </div>
        <div className="record-panel-body">
          <label className="field-control">
            <span>Owner Record</span>
            <input
              aria-label="Owner record"
              value={ownerRecord}
              onChange={(event) => setOwnerRecord(event.target.value)}
              placeholder="Optional: filter or target upload by record id"
            />
          </label>
          <label className="field-control">
            <span>Document Type</span>
            <input
              aria-label="Document type"
              value={documentType}
              onChange={(event) => setDocumentType(event.target.value)}
              placeholder="Optional filter"
            />
          </label>
          <DocumentPanel
            documents={documents}
            ownerRecordId={ownerFilter}
            isUploading={uploadDocument.isPending}
            onUpload={(file, metadata) => uploadDocument.mutate({ file, metadata })}
            onRelease={(documentId, revisionId) => releaseDocument.mutate({ documentId, revisionId })}
          />
        </div>
      </section>

      {documentsQuery.error && (
        <div className="admin-alert" role="alert">
          <strong>Document list failed</strong>
          <span>{errorMessage(documentsQuery.error)}</span>
        </div>
      )}

      {uploadError && (
        <div className="admin-alert" role="alert">
          <strong>Document action failed</strong>
          <span>{errorMessage(uploadError)}</span>
        </div>
      )}
    </div>
  );
}

export function DocumentDetailPage() {
  const { documentId = "" } = useParams();
  const queryClient = useQueryClient();

  const documentQuery = useQuery({
    queryKey: ["documents", documentId],
    queryFn: () => apiGet<DocumentItem>(`/documents/${documentId}/`),
    enabled: Boolean(documentId)
  });

  const releaseDocument = useMutation({
    mutationFn: ({ documentId, revisionId }: { documentId: string | number; revisionId: string | number }) =>
      apiPost<DocumentItem>(`/documents/${documentId}/revisions/${revisionId}/release/`, {}),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["documents", documentId] });
      void queryClient.invalidateQueries({ queryKey: ["documents", "list"] });
    }
  });

  if (documentQuery.isLoading) {
    return (
      <div className="empty-state">
        <FileText aria-hidden="true" size={24} />
        <div>
          <h2>Loading document</h2>
          <p>Fetching document metadata and revisions.</p>
        </div>
      </div>
    );
  }

  if (!documentQuery.data) {
    return (
      <div className="empty-state" role="alert">
        <FileText aria-hidden="true" size={24} />
        <div>
          <h2>Document not found</h2>
          <p>The requested document could not be loaded.</p>
        </div>
      </div>
    );
  }

  const document = documentQuery.data;
  const revisionCount = document.revisions?.length ?? 0;

  return (
    <div className="page-stack">
      <section className="workspace-header" aria-labelledby="document-detail-title">
        <div>
          <p className="section-kicker">Controlled document</p>
          <h1 id="document-detail-title">
            {document.title ?? document.name ?? `Document ${document.id}`}
          </h1>
        </div>
      </section>
      <section className="table-panel detail-panel" aria-labelledby="document-metadata-title">
        <div className="panel-heading">
          <div>
            <p className="section-kicker">Document metadata</p>
            <h2 id="document-metadata-title">Document {document.id}</h2>
          </div>
          <StatusBadge tone={document.state === "released" ? "ready" : "active"}>
            {document.state ?? "Draft"}
          </StatusBadge>
        </div>
        <dl className="definition-list">
          <div>
            <dt>Type</dt>
            <dd>{document.document_type ?? "Not set"}</dd>
          </div>
          <div>
            <dt>Owner Record</dt>
            <dd>
              {document.owner_record ? (
                <Link to={`/records/${document.owner_record}`}>{ownerRecordLabel(document)}</Link>
              ) : (
                "Not set"
              )}
            </dd>
          </div>
          <div>
            <dt>Revisions</dt>
            <dd>{revisionCount}</dd>
          </div>
        </dl>
      </section>

      <section className="detail-grid">
        <DocumentPanel
          documents={[document]}
          ownerRecordId={document.owner_record}
          onRelease={(documentId, revisionId) => releaseDocument.mutate({ documentId, revisionId })}
        />
      </section>
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

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Document request failed.";
}

function asDocumentList(response?: DocumentItem[] | DocumentListResponse) {
  if (!response) {
    return [];
  }
  return Array.isArray(response) ? response : response.results ?? [];
}

function documentsQueryString(ownerRecord: string, documentType: string) {
  const params = new URLSearchParams();
  if (ownerRecord) {
    params.set("owner_record", ownerRecord);
  }
  if (documentType) {
    params.set("document_type", documentType);
  }
  const query = params.toString();
  return query ? `?${query}` : "";
}

function DocumentListItem({
  document,
  onRelease
}: {
  document: DocumentItem;
  onRelease?: (documentId: string | number, revisionId: string | number) => void;
}) {
  const revision = currentRevision(document);
  const status = document.state ?? document.status ?? "draft";

  return (
    <article className="document-item" role="listitem">
      <div className="document-main">
        <strong>
          <Link className="text-link" to={`/documents/${document.id}`}>
            {document.title ?? document.name ?? document.filename ?? document.id}
          </Link>
        </strong>
        <span>
          Extraction:{" "}
          {document.extraction_status ?? revision?.extraction_status ?? "not started"}
        </span>
        {document.owner_record && (
          <Link className="text-link" to={`/records/${document.owner_record}`}>
            Owner record: {ownerRecordLabel(document)}
          </Link>
        )}
      </div>
      <StatusBadge tone={status === "released" ? "ready" : "review"}>{status}</StatusBadge>
      <RevisionHistory revisions={revision ? [revision] : document.revisions ?? []} />
      <div className="document-actions">
        <a
          className="button button-secondary"
          href={document.preview_url ?? `/api/documents/${document.id}/preview/`}
        >
          <Eye aria-hidden="true" size={16} />
          Preview
        </a>
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
        <a
          className="button button-secondary"
          href={document.audit_url ?? `/api/documents/${document.id}/audit/`}
        >
          <LinkIcon aria-hidden="true" size={16} />
          Audit
        </a>
      </div>
    </article>
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

function ownerRecordLabel(document: DocumentItem) {
  const code = document.owner_record_code?.trim();
  const title = document.owner_record_title?.trim();
  if (code && title) {
    return `${code} - ${title}`;
  }
  return code || title || String(document.owner_record ?? "Not set");
}

function formatDate(value?: string) {
  if (!value) {
    return "";
  }

  return new Intl.DateTimeFormat("en", { dateStyle: "medium" }).format(new Date(value));
}

