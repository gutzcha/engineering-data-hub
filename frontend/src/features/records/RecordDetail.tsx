import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Archive,
  ClipboardCheck,
  History,
  Loader2,
  Rocket,
  Save
} from "lucide-react";
import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { StatusBadge } from "../../components/StatusBadge";
import {
  DocumentItem,
  DocumentPanel,
  buildDocumentUploadForm
} from "../documents/DocumentPanel";
import { FolderEvent, FolderInfo, FolderPanel } from "../folders/FolderPanel";
import { WorkflowPanel as WorkflowStatusPanel } from "../workflows/WorkflowPanel";
import { apiGet, apiPatch, apiPost, apiPostForm } from "../../lib/api";
import {
  ConfigData,
  DynamicRecordForm,
  RecordValues,
  findObjectType
} from "./DynamicRecordForm";
import { EntityGraph, EntityGraphPanel } from "./EntityGraphPanel";

type ConfigVersion = {
  data?: ConfigData;
};

type RecordDetailData = {
  id: string | number;
  code?: string;
  title?: string;
  name?: string;
  object_type_key?: string;
  object_type?: { key?: string; label?: string };
  status?: string;
  data?: RecordValues;
  fields?: RecordValues;
  folder?: FolderInfo;
  documents?: DocumentItem[];
  workflow_state?: string;
  project_links?: ProjectLink[];
  projects?: ProjectLink[];
  created_at?: string;
  updated_at?: string;
};

type ProjectLink = {
  id?: string | number;
  code?: string;
  title?: string;
  name?: string;
};

type WorkflowState = {
  state?: string;
  status?: string;
  transitions?: WorkflowTransition[];
  available_transitions?: WorkflowTransition[];
};

type WorkflowTransition = {
    key?: string;
    id?: string | number;
    label?: string;
    name?: string;
    to?: string;
    to_state?: string;
};

type AuditEvent = {
  id?: string | number;
  action?: string;
  actor?: string;
  user?: string;
  created_at?: string;
  timestamp?: string;
};

type AuditResponse = AuditEvent[] | { results?: AuditEvent[] };
type FolderEventsResponse = FolderEvent[] | { results?: FolderEvent[] };

type RecordVersion = {
  id: string | number;
  version_number?: number;
  snapshot?: {
    title?: string;
    status?: string;
    data?: RecordValues;
  };
  change_note?: string;
  created_by?: string | number | null;
  created_at?: string;
};

type RecordVersionsResponse = RecordVersion[] | { results?: RecordVersion[] };

export function RecordDetail() {
  const { recordId = "" } = useParams();
  const queryClient = useQueryClient();
  const [draftValues, setDraftValues] = useState<RecordValues>({});
  const [archiveConfirmation, setArchiveConfirmation] = useState(false);
  const [versionNote, setVersionNote] = useState("");
  const [versionNotice, setVersionNotice] = useState("");

  const configQuery = useQuery({
    queryKey: ["config", "active"],
    queryFn: () => apiGet<ConfigVersion>("/config/active/")
  });

  const recordQuery = useQuery({
    queryKey: ["records", recordId],
    queryFn: () => apiGet<RecordDetailData>(`/records/${recordId}/`),
    enabled: Boolean(recordId)
  });

  const graphQuery = useQuery({
    queryKey: ["records", recordId, "graph"],
    queryFn: () => apiGet<EntityGraph>(`/records/${recordId}/graph/`),
    enabled: Boolean(recordId)
  });

  const folderEventsQuery = useQuery({
    queryKey: ["folder-events", "record", recordId],
    queryFn: () => apiGet<FolderEventsResponse>(`/folder-events/?record=${recordId}`),
    enabled: Boolean(recordId)
  });

  const workflowQuery = useQuery({
    queryKey: ["records", recordId, "workflow"],
    queryFn: () => apiGet<WorkflowState>(`/records/${recordId}/workflow/`),
    enabled: Boolean(recordId)
  });

  const auditQuery = useQuery({
    queryKey: ["audit", "records", recordId],
    queryFn: () => apiGet<AuditResponse>(`/audit/records/${recordId}/`),
    enabled: Boolean(recordId)
  });

  const versionsQuery = useQuery({
    queryKey: ["records", recordId, "versions"],
    queryFn: () => apiGet<RecordVersionsResponse>(`/records/${recordId}/versions/`),
    enabled: Boolean(recordId)
  });

  const saveRecord = useMutation({
    mutationFn: (data: RecordValues) =>
      apiPatch<RecordDetailData>(`/records/${recordId}/`, { data }),
    onSuccess: (updatedRecord) => {
      queryClient.setQueryData(["records", recordId], updatedRecord);
    }
  });

  const releaseRecord = useMutation({
    mutationFn: () => apiPost<RecordDetailData>(`/records/${recordId}/release/`, {}),
    onSuccess: (updatedRecord) => {
      queryClient.setQueryData(["records", recordId], updatedRecord);
    }
  });

  const archiveRecord = useMutation({
    mutationFn: () => apiPost<RecordDetailData>(`/records/${recordId}/archive/`, {}),
    onSuccess: (updatedRecord) => {
      setArchiveConfirmation(false);
      queryClient.setQueryData(["records", recordId], updatedRecord);
      void queryClient.invalidateQueries({ queryKey: ["records"] });
      void queryClient.invalidateQueries({ queryKey: ["audit", "records", recordId] });
    }
  });

  const createVersion = useMutation({
    mutationFn: () =>
      apiPost<RecordVersion>(`/records/${recordId}/versions/`, {
        change_note: versionNote.trim()
      }),
    onSuccess: (version) => {
      setVersionNote("");
      setVersionNotice(`Version ${version.version_number ?? version.id} created.`);
      void queryClient.invalidateQueries({ queryKey: ["records", recordId, "versions"] });
      void queryClient.invalidateQueries({ queryKey: ["audit", "records", recordId] });
    }
  });

  const generateFolder = useMutation({
    mutationFn: () => apiPost<FolderInfo>(`/records/${recordId}/folders/generate/`, {}),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["records", recordId] });
      void queryClient.invalidateQueries({ queryKey: ["folder-events", "record", recordId] });
    }
  });

  const releaseDocument = useMutation({
    mutationFn: ({
      documentId,
      revisionId
    }: {
      documentId: string | number;
      revisionId: string | number;
    }) =>
      apiPost<DocumentItem>(
        `/documents/${documentId}/revisions/${revisionId}/release/`,
        {}
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["records", recordId] });
    }
  });

  const uploadDocument = useMutation({
    mutationFn: ({
      file,
      metadata
    }: {
      file: File;
      metadata: Parameters<typeof buildDocumentUploadForm>[1];
    }) =>
      apiPostForm<DocumentItem>(
        "/documents/",
        buildDocumentUploadForm(file, { ...metadata, owner_record: recordId })
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["records", recordId] });
    }
  });

  const acceptFolderEvent = useMutation({
    mutationFn: (eventId: string | number) =>
      apiPost<FolderEvent>(`/folder-events/${eventId}/accept/`, {}),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["folder-events", "record", recordId] });
    }
  });

  const ignoreFolderEvent = useMutation({
    mutationFn: (eventId: string | number) =>
      apiPost<FolderEvent>(`/folder-events/${eventId}/ignore/`, {}),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["folder-events", "record", recordId] });
    }
  });

  const record = recordQuery.data;
  const config = configQuery.data?.data;
  const objectTypeKey = record?.object_type_key ?? record?.object_type?.key;
  const objectType = findObjectType(config, objectTypeKey);
  const recordValues = record?.data ?? record?.fields ?? {};
  const editableValues = { ...recordValues, ...draftValues };

  const title = useMemo(
    () => recordTitle(record, objectType?.title_field),
    [objectType?.title_field, record]
  );

  if (recordQuery.isLoading || configQuery.isLoading) {
    return (
      <div className="empty-state">
        <Loader2 aria-hidden="true" size={24} />
        <div>
          <h2>Loading Record</h2>
          <p>Fetching the record and published configuration.</p>
        </div>
      </div>
    );
  }

  if (!record) {
    return (
      <div className="empty-state" role="alert">
        <ClipboardCheck aria-hidden="true" size={24} />
        <div>
          <h2>Record unavailable</h2>
          <p>The requested record could not be loaded.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page-stack record-detail">
      <section className="workspace-header" aria-labelledby="record-detail-title">
        <div>
          <p className="section-kicker">
            {objectType?.label ?? record.object_type?.label ?? "Record"} {record.code ?? record.id}
          </p>
          <h1 id="record-detail-title">{title}</h1>
        </div>
        <div className="header-actions">
          <button
            className="button button-secondary"
            type="button"
            onClick={() => saveRecord.mutate(editableValues)}
            disabled={saveRecord.isPending}
          >
            {saveRecord.isPending ? (
              <Loader2 aria-hidden="true" size={16} />
            ) : (
              <Save aria-hidden="true" size={16} />
            )}
            Save Fields
          </button>
          <button
            className="button button-primary"
            type="button"
            onClick={() => releaseRecord.mutate()}
            disabled={releaseRecord.isPending}
          >
            <Rocket aria-hidden="true" size={16} />
            Release
          </button>
          <button
            className="button button-secondary"
            type="button"
            onClick={() =>
              archiveConfirmation ? archiveRecord.mutate() : setArchiveConfirmation(true)
            }
            disabled={archiveRecord.isPending || record.status === "archived"}
          >
            {archiveRecord.isPending ? (
              <Loader2 aria-hidden="true" size={16} />
            ) : (
              <Archive aria-hidden="true" size={16} />
            )}
            {archiveConfirmation ? "Confirm Archive" : "Archive"}
          </button>
        </div>
      </section>

      {archiveConfirmation && (
        <div className="admin-alert" role="status">
          <strong>Archive record?</strong>
          <span>This keeps record history and removes it from active work. Records are not deleted.</span>
        </div>
      )}

      {(recordQuery.error ||
        configQuery.error ||
        saveRecord.error ||
        releaseRecord.error ||
        archiveRecord.error ||
        createVersion.error) && (
        <div className="admin-alert" role="alert">
          <strong>Record action failed</strong>
          <span>
            {errorMessage(
              recordQuery.error ??
                configQuery.error ??
                saveRecord.error ??
                releaseRecord.error ??
                archiveRecord.error ??
                createVersion.error
            )}
          </span>
        </div>
      )}

      <section className="admin-status-row" aria-label="Record summary">
        <SummaryMetric label="Status" value={record.status ?? "Unknown"} />
        <SummaryMetric label="Workflow" value={workflowQuery.data?.state ?? record.workflow_state ?? "Not started"} />
        <SummaryMetric label="Updated" value={formatDateTime(record.updated_at)} />
        <SummaryMetric label="Object type" value={objectType?.label ?? objectTypeKey ?? "Unconfigured"} />
      </section>

      <section className="table-panel detail-panel" aria-labelledby="editable-fields-title">
        <div className="panel-heading">
          <div>
            <p className="section-kicker">Editable fields</p>
            <h2 id="editable-fields-title">Record Fields</h2>
          </div>
          <StatusBadge tone={saveRecord.isSuccess ? "ready" : "neutral"}>
            {saveRecord.isSuccess ? "Saved" : "Draft"}
          </StatusBadge>
        </div>
        <div className="record-panel-body">
          <DynamicRecordForm
            config={config}
            objectTypeKey={objectTypeKey}
            values={editableValues}
            onChange={setDraftValues}
          />
        </div>
      </section>

      <div className="detail-grid">
        <EntityGraphPanel graph={graphQuery.data} isLoading={graphQuery.isLoading} />
        <FolderPanel
          folder={record.folder}
          events={itemsFromResponse(folderEventsQuery.data)}
          isGenerating={generateFolder.isPending}
          onGenerate={() => generateFolder.mutate()}
          onAcceptEvent={(eventId) => acceptFolderEvent.mutate(eventId)}
          onIgnoreEvent={(eventId) => ignoreFolderEvent.mutate(eventId)}
        />
        <DocumentPanel
          documents={record.documents}
          ownerRecordId={recordId}
          isUploading={uploadDocument.isPending}
          onUpload={(file, metadata) => uploadDocument.mutate({ file, metadata })}
          onRelease={(documentId, revisionId) =>
            releaseDocument.mutate({ documentId, revisionId })
          }
        />
        <WorkflowStatusPanel
          recordId={recordId}
          workflow={workflowQuery.data}
          isLoading={workflowQuery.isLoading}
        />
        <ProjectLinksPanel projects={record.project_links ?? record.projects ?? []} />
        <VersionHistoryPanel
          error={versionsQuery.error}
          isCreating={createVersion.isPending}
          isLoading={versionsQuery.isLoading}
          note={versionNote}
          notice={versionNotice}
          onCreate={() => {
            setVersionNotice("");
            createVersion.mutate();
          }}
          onNoteChange={(note) => {
            setVersionNotice("");
            setVersionNote(note);
          }}
          versions={itemsFromResponse(versionsQuery.data)}
        />
        <AuditPanel events={itemsFromResponse(auditQuery.data)} isLoading={auditQuery.isLoading} />
      </div>
    </div>
  );
}

function SummaryMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="admin-stat">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function ProjectLinksPanel({ projects }: { projects: ProjectLink[] }) {
  return (
    <section className="table-panel detail-panel" aria-labelledby="project-links-title">
      <div className="panel-heading">
        <div>
          <p className="section-kicker">Project links</p>
          <h2 id="project-links-title">Projects</h2>
        </div>
        <StatusBadge tone={projects.length ? "active" : "neutral"}>
          {projects.length} Links
        </StatusBadge>
      </div>
      <div className="record-panel-body link-list">
        {projects.length === 0 ? (
          <p className="admin-muted">No linked projects.</p>
        ) : (
          projects.map((project) => (
            <Link to={`/projects/${project.id ?? project.code}`} key={project.id ?? project.code}>
              <strong>{project.title ?? project.name ?? project.code ?? project.id}</strong>
              <span>{project.code ?? "Project"}</span>
            </Link>
          ))
        )}
      </div>
    </section>
  );
}

function VersionHistoryPanel({
  error,
  isCreating,
  isLoading,
  note,
  notice,
  onCreate,
  onNoteChange,
  versions
}: {
  error: unknown;
  isCreating: boolean;
  isLoading: boolean;
  note: string;
  notice: string;
  onCreate: () => void;
  onNoteChange: (note: string) => void;
  versions: RecordVersion[];
}) {
  return (
    <section className="table-panel detail-panel" aria-labelledby="record-version-title">
      <div className="panel-heading">
        <div>
          <p className="section-kicker">Controlled snapshots</p>
          <h2 id="record-version-title">Version History</h2>
        </div>
        <StatusBadge tone={versions.length ? "active" : "neutral"}>
          {isLoading ? "Loading" : `${versions.length} Versions`}
        </StatusBadge>
      </div>
      <div className="record-panel-body">
        {notice && <div className="validation-success">{notice}</div>}
        {error ? (
          <div className="admin-alert" role="alert">
            <strong>Version history failed</strong>
            <span>{errorMessage(error)}</span>
          </div>
        ) : null}
        <div className="admin-form-grid">
          <label className="field-control">
            <span>Change Note</span>
            <input
              aria-label="Version change note"
              value={note}
              onChange={(event) => onNoteChange(event.target.value)}
            />
          </label>
          <button
            className="button button-secondary"
            type="button"
            onClick={onCreate}
            disabled={isCreating}
          >
            {isCreating ? (
              <Loader2 aria-hidden="true" size={16} />
            ) : (
              <History aria-hidden="true" size={16} />
            )}
            Create Version
          </button>
        </div>
        <div className="event-list" role="list" aria-label="Record versions">
          {versions.length === 0 ? (
            <p className="admin-muted">{isLoading ? "Loading versions." : "No versions recorded."}</p>
          ) : (
            versions.map((version) => (
              <article className="event-item" role="listitem" key={version.id}>
                <div>
                  <strong>Version {version.version_number ?? version.id}</strong>
                  <span>
                    {[version.snapshot?.title, version.snapshot?.status, version.change_note]
                      .filter(Boolean)
                      .join(" · ") || "Snapshot recorded"}
                  </span>
                  <span>{formatDateTime(version.created_at)}</span>
                </div>
              </article>
            ))
          )}
        </div>
      </div>
    </section>
  );
}

function AuditPanel({
  events,
  isLoading
}: {
  events: AuditEvent[];
  isLoading: boolean;
}) {
  return (
    <section className="table-panel detail-panel" aria-labelledby="audit-history-title">
      <div className="panel-heading">
        <div>
          <p className="section-kicker">Audit history</p>
          <h2 id="audit-history-title">Audit History</h2>
        </div>
        <History aria-hidden="true" size={18} />
      </div>
      <div className="record-panel-body event-list" role="list" aria-label="Audit history">
        {events.length === 0 ? (
          <p className="admin-muted">{isLoading ? "Loading audit history." : "No audit events recorded."}</p>
        ) : (
          events.map((event, index) => (
            <div className="event-item" role="listitem" key={event.id ?? index}>
              <div>
                <strong>{event.action ?? "updated"}</strong>
                <span>
                  {event.actor ?? event.user ?? "System"} · {formatDateTime(event.created_at ?? event.timestamp)}
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </section>
  );
}

function recordTitle(record?: RecordDetailData, titleField?: string) {
  if (!record) {
    return "Record";
  }

  const data = record.data ?? record.fields ?? {};
  const configuredTitle =
    titleField && data[titleField] !== undefined ? String(data[titleField]) : undefined;

  return configuredTitle ?? record.title ?? record.name ?? record.code ?? `Record ${record.id}`;
}

function formatDateTime(value?: string) {
  if (!value) {
    return "Not recorded";
  }

  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Record request failed.";
}

function itemsFromResponse<T>(response?: T[] | { results?: T[] }) {
  if (Array.isArray(response)) {
    return response;
  }

  return response?.results ?? [];
}
