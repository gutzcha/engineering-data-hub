import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  FileCheck2,
  History,
  Loader2,
  Rocket,
  Save,
  ShieldCheck
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { StatusBadge } from "../../components/StatusBadge";
import { apiGet, apiPatch, apiPost } from "../../lib/api";
import { FolderTemplateEditor } from "./FolderTemplateEditor";
import { FormLayoutEditor } from "./FormLayoutEditor";
import { ObjectTypeEditor } from "./ObjectTypeEditor";
import { WorkflowEditor } from "./WorkflowEditor";

export type FieldDefinition = {
  key: string;
  label: string;
  type: string;
  required?: boolean;
  searchable?: boolean;
  unique?: boolean;
  options?: string[];
  reference_target_type?: string;
};

export type ObjectTypeDefinition = {
  key: string;
  label: string;
  plural_label?: string;
  code_pattern?: string;
  title_field?: string;
  folder_template_key?: string;
  default_workflow_key?: string;
  fields: FieldDefinition[];
};

export type FormLayoutDefinition = {
  key: string;
  object_type_key?: string;
  sections?: Array<{
    label: string;
    fields: string[];
  }>;
};

export type FolderTemplateDefinition = {
  key: string;
  label?: string;
  pattern: string;
};

export type WorkflowDefinition = {
  key: string;
  label?: string;
  states?: string[];
  transitions?: Array<{
    from: string;
    to: string;
    guard?: string;
    task_template?: string;
  }>;
  release_rules?: string[];
};

export type ConfigData = {
  object_types: ObjectTypeDefinition[];
  form_layouts?: FormLayoutDefinition[];
  folder_templates?: FolderTemplateDefinition[];
  workflows?: WorkflowDefinition[];
  relationship_types?: unknown[];
  dashboards?: unknown[];
};

type ConfigVersion = {
  id: number;
  version: number;
  data: ConfigData;
  published_at?: string;
  published_by?: number | null;
};

type ConfigDraft = {
  id: number;
  status: string;
  data: ConfigData;
  created_at?: string;
  updated_at?: string;
};

type ValidationError = {
  path: string;
  code: string;
  message: string;
};

type WorkspaceView = "current" | "draft" | "validation" | "publish" | "history";

const emptyConfig: ConfigData = {
  object_types: [],
  form_layouts: [],
  folder_templates: [],
  workflows: [],
  relationship_types: [],
  dashboards: []
};

const sampleRecord = {
  code: "PROD-000123",
  commercial_name: "Clear Film",
  material_name: "Resin A",
  supplier_name: "North Resin",
  project_name: "Cost Down"
};

export function ConfigWorkspace() {
  const queryClient = useQueryClient();
  const [activeView, setActiveView] = useState<WorkspaceView>("current");
  const [draft, setDraft] = useState<ConfigDraft | null>(null);
  const [draftData, setDraftData] = useState<ConfigData>(emptyConfig);
  const [validationErrors, setValidationErrors] = useState<ValidationError[] | null>(
    null
  );
  const [breakingChanges, setBreakingChanges] = useState<ValidationError[]>([]);
  const [breakingChangeConfirmed, setBreakingChangeConfirmed] = useState(false);
  const [selectedObjectTypeKey, setSelectedObjectTypeKey] = useState("");

  const activeConfigQuery = useQuery({
    queryKey: ["admin-config", "active"],
    queryFn: () => apiGet<ConfigVersion>("/config/active/")
  });

  const publishHistoryQuery = useQuery({
    queryKey: ["admin-config", "history"],
    queryFn: () => apiGet<ConfigVersion[]>("/config/history/")
  });

  const createDraft = useMutation({
    mutationFn: () => apiPost<ConfigDraft>("/config/drafts/", {}),
    onSuccess: (createdDraft) => {
      setDraft(createdDraft);
      setDraftData(normalizeConfigData(createdDraft.data));
      setValidationErrors(null);
      setBreakingChanges([]);
      setBreakingChangeConfirmed(false);
      setActiveView("draft");
    }
  });

  const validateDraft = useMutation({
    mutationFn: async () => {
      if (!draft) {
        throw new Error("Create a draft before validating.");
      }

      await persistDraftData(draft.id);
      return apiPost<{ errors: ValidationError[]; breaking_changes?: ValidationError[] }>(
        `/config/drafts/${draft.id}/validate/`,
        {}
      );
    },
    onSuccess: (result) => {
      setValidationErrors(result.errors);
      setBreakingChanges(result.breaking_changes ?? []);
      setBreakingChangeConfirmed(false);
      setActiveView("validation");
    },
    onError: (error) => {
      const message = errorMessage(error);
      setValidationErrors([{ path: "validate", code: "validate_failed", message }]);
      setBreakingChanges([]);
      setBreakingChangeConfirmed(false);
      setActiveView("validation");
    }
  });

  const publishDraft = useMutation({
    mutationFn: async () => {
      if (!draft) {
        throw new Error("Create and validate a draft before publishing.");
      }

      await persistDraftData(draft.id);
      const publishPayload = breakingChanges.length
        ? { confirm_breaking_changes: breakingChangeConfirmed }
        : {};
      return apiPost<ConfigVersion>(`/config/drafts/${draft.id}/publish/`, publishPayload);
    },
    onSuccess: (publishedVersion) => {
      setDraft(null);
      setValidationErrors(null);
      setBreakingChanges([]);
      setBreakingChangeConfirmed(false);
      setDraftData(normalizeConfigData(publishedVersion.data));
      setActiveView("history");
      queryClient.setQueryData(["admin-config", "active"], publishedVersion);
      queryClient.setQueryData(["config", "active"], publishedVersion);
      queryClient.setQueryData<ConfigVersion[]>(
        ["admin-config", "history"],
        (current = []) => mergeHistory(current, publishedVersion)
      );
    },
    onError: async (error) => {
      const message = error instanceof Error ? error.message : "Publish failed.";
      setValidationErrors([{ path: "publish", code: "publish_failed", message }]);
      setActiveView("validation");
    }
  });

  const activeConfig = activeConfigQuery.data;
  const currentData = normalizeConfigData(activeConfig?.data ?? emptyConfig);
  const editableData = draft ? draftData : currentData;
  const publishHistory = publishHistoryQuery.data ?? [];
  const workspaceError =
    createDraft.error ?? validateDraft.error ?? publishDraft.error ?? null;
  const validationPassed =
    workspaceError === null && validationErrors !== null && validationErrors.length === 0;
  const hasDraft = draft !== null;
  const publishBlockedByBreakingChanges =
    breakingChanges.length > 0 && !breakingChangeConfirmed;

  const objectTypeSummary = useMemo(() => {
    const count = editableData.object_types.length;
    const fieldCount = editableData.object_types.reduce(
      (total, objectType) => total + objectType.fields.length,
      0
    );
    return { count, fieldCount };
  }, [editableData.object_types]);

  useEffect(() => {
    const objectTypes = editableData.object_types;
    if (objectTypes.length === 0) {
      setSelectedObjectTypeKey("");
      return;
    }
    if (!objectTypes.some((objectType) => objectType.key === selectedObjectTypeKey)) {
      setSelectedObjectTypeKey(objectTypes[0].key);
    }
  }, [editableData.object_types, selectedObjectTypeKey]);

  function updateDraftData(updater: (data: ConfigData) => ConfigData) {
    setDraftData((current) => updater(normalizeConfigData(current)));
    setValidationErrors(null);
    setBreakingChanges([]);
    setBreakingChangeConfirmed(false);
  }

  async function persistDraftData(draftId: number) {
    const updatedDraft = await apiPatch<ConfigDraft>(`/config/drafts/${draftId}/`, {
      data: draftData
    });
    setDraft(updatedDraft);
    setDraftData(normalizeConfigData(updatedDraft.data));
    return updatedDraft;
  }

  return (
    <div className="page-stack admin-config">
      <section className="workspace-header" aria-labelledby="admin-config-title">
        <div>
          <p className="section-kicker">System controls</p>
          <h1 id="admin-config-title">Admin Configuration</h1>
        </div>
        <div className="header-actions">
          <button
            className="button button-secondary"
            type="button"
            onClick={() => createDraft.mutate()}
            disabled={createDraft.isPending}
          >
            {createDraft.isPending ? (
              <Loader2 aria-hidden="true" size={16} />
            ) : (
              <Save aria-hidden="true" size={16} />
            )}
            Create Draft
          </button>
          <button
            className="button button-secondary"
            type="button"
            onClick={() => validateDraft.mutate()}
            disabled={!hasDraft || validateDraft.isPending}
          >
            {validateDraft.isPending ? (
              <Loader2 aria-hidden="true" size={16} />
            ) : (
              <FileCheck2 aria-hidden="true" size={16} />
            )}
            Validate Draft
          </button>
          <button
            className="button button-primary"
            type="button"
            onClick={() => publishDraft.mutate()}
            disabled={
              !hasDraft ||
              !validationPassed ||
              publishBlockedByBreakingChanges ||
              publishDraft.isPending
            }
          >
            <Rocket aria-hidden="true" size={16} />
            Publish Configuration
          </button>
        </div>
      </section>

      {workspaceError && (
        <div className="admin-alert" role="alert">
          <strong>Configuration action failed</strong>
          <span>{errorMessage(workspaceError)}</span>
        </div>
      )}

      <section className="admin-status-row" aria-label="Configuration status">
        <div className="admin-stat">
          <span>Current published version</span>
          <strong>
            {activeConfigQuery.isLoading
              ? "Loading"
              : activeConfig
                ? `Published v${activeConfig.version}`
                : "No published version"}
          </strong>
        </div>
        <div className="admin-stat">
          <span>Draft</span>
          <strong>{draft ? `Draft #${draft.id}` : "No active draft"}</strong>
        </div>
        <div className="admin-stat">
          <span>Object model</span>
          <strong>
            {objectTypeSummary.count} types / {objectTypeSummary.fieldCount} fields
          </strong>
        </div>
        <div className="admin-stat">
          <span>Validation</span>
          <strong>{validationStatusLabel(validationErrors)}</strong>
        </div>
      </section>

      <div className="segmented-tabs" role="tablist" aria-label="Configuration views">
        {workspaceTabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.value}
              type="button"
              role="tab"
              aria-selected={activeView === tab.value}
              className={
                activeView === tab.value
                  ? "segmented-tab segmented-tab-active"
                  : "segmented-tab"
              }
              onClick={() => setActiveView(tab.value)}
            >
              <Icon aria-hidden="true" size={15} />
              {tab.label}
            </button>
          );
        })}
      </div>

      {activeView === "current" && (
        <CurrentVersionView config={activeConfig} isLoading={activeConfigQuery.isLoading} />
      )}

      {activeView === "draft" && (
        <DraftEditorView
          data={editableData}
          selectedObjectTypeKey={selectedObjectTypeKey}
          readOnly={!draft}
          onChange={updateDraftData}
          onSelectObjectType={setSelectedObjectTypeKey}
        />
      )}

      {activeView === "validation" && (
        <ValidationView
          errors={validationErrors}
          breakingChanges={breakingChanges}
          isValidating={validateDraft.isPending}
          hasDraft={hasDraft}
        />
      )}

      {activeView === "publish" && (
        <PublishView
          draft={draft}
          validationPassed={validationPassed}
          breakingChanges={breakingChanges}
          breakingChangeConfirmed={breakingChangeConfirmed}
          isPublishing={publishDraft.isPending}
          onValidate={() => validateDraft.mutate()}
          onPublish={() => publishDraft.mutate()}
          onBreakingChangeConfirmed={setBreakingChangeConfirmed}
        />
      )}

      {activeView === "history" && <PublishHistoryView history={publishHistory} />}
    </div>
  );
}

function CurrentVersionView({
  config,
  isLoading
}: {
  config?: ConfigVersion;
  isLoading: boolean;
}) {
  const data = normalizeConfigData(config?.data ?? emptyConfig);

  return (
    <section className="table-panel admin-panel" aria-labelledby="current-version-title">
      <div className="panel-heading">
        <div>
          <p className="section-kicker">Current published version</p>
          <h2 id="current-version-title">
            {config ? `Published v${config.version}` : "Published Configuration"}
          </h2>
        </div>
        <StatusBadge tone={config ? "ready" : "neutral"}>
          {isLoading ? "Loading" : config ? "Active" : "Unavailable"}
        </StatusBadge>
      </div>
      <div className="admin-panel-body">
        <DefinitionList
          items={[
            ["Object types", data.object_types.length.toString()],
            ["Form layouts", (data.form_layouts ?? []).length.toString()],
            ["Folder templates", (data.folder_templates ?? []).length.toString()],
            ["Workflows", (data.workflows ?? []).length.toString()],
            ["Published at", formatDateTime(config?.published_at)]
          ]}
        />
      </div>
    </section>
  );
}

function DraftEditorView({
  data,
  selectedObjectTypeKey,
  readOnly,
  onChange,
  onSelectObjectType
}: {
  data: ConfigData;
  selectedObjectTypeKey: string;
  readOnly: boolean;
  onChange: (updater: (data: ConfigData) => ConfigData) => void;
  onSelectObjectType: (objectTypeKey: string) => void;
}) {
  const selectedObjectType =
    data.object_types.find((candidate) => candidate.key === selectedObjectTypeKey) ??
    data.object_types[0];
  const objectType = selectedObjectType ?? defaultObjectType();
  const formLayout =
    data.form_layouts?.find((layout) => layout.object_type_key === objectType.key) ??
    data.form_layouts?.[0] ??
    defaultFormLayout(objectType.key);
  const folderTemplate =
    data.folder_templates?.[0] ?? defaultFolderTemplate(objectType.folder_template_key);
  const workflow = data.workflows?.[0] ?? defaultWorkflow(objectType.default_workflow_key);

  function addField() {
    onChange((current) => {
      const normalized = normalizeConfigData(current);
      const currentObjectType =
        normalized.object_types.find((candidate) => candidate.key === objectType.key) ??
        objectType;
      const newField = defaultFieldDefinition(currentObjectType.fields);
      const updatedObjectType = {
        ...currentObjectType,
        fields: [...currentObjectType.fields, newField]
      };
      const currentLayout =
        findFormLayout(normalized.form_layouts ?? [], currentObjectType.key) ??
        defaultFormLayout(updatedObjectType.key);
      const updatedLayout = addFieldToFirstLayoutSection(
        currentLayout,
        newField.key,
        updatedObjectType.key
      );

      return {
        ...normalized,
        object_types: replaceObjectType(
          normalized.object_types,
          currentObjectType.key,
          updatedObjectType
        ),
        form_layouts: replaceFormLayout(
          normalized.form_layouts ?? [],
          currentLayout.key,
          updatedLayout
        )
      };
    });
  }

  function removeField(fieldKey: string) {
    onChange((current) => {
      const normalized = normalizeConfigData(current);
      const currentObjectType =
        normalized.object_types.find((candidate) => candidate.key === objectType.key) ??
        objectType;
      const updatedObjectType = {
        ...currentObjectType,
        fields: currentObjectType.fields.filter((field) => field.key !== fieldKey),
        title_field:
          currentObjectType.title_field === fieldKey ? "" : currentObjectType.title_field
      };

      return {
        ...normalized,
        object_types: replaceObjectType(
          normalized.object_types,
          currentObjectType.key,
          updatedObjectType
        ),
        form_layouts: removeFieldFromLayouts(
          normalized.form_layouts ?? [],
          currentObjectType.key,
          fieldKey
        )
      };
    });
  }

  return (
    <div className="admin-editor-grid">
      {readOnly && (
        <div className="admin-inline-note">
          Create a draft to enable editing. Current values are shown for review.
        </div>
      )}
      <section className="table-panel admin-panel" aria-labelledby="object-type-selector-title">
        <div className="panel-heading">
          <div>
            <p className="section-kicker">Schema target</p>
            <h2 id="object-type-selector-title">Object Type</h2>
          </div>
        </div>
        <div className="admin-panel-body">
          <label className="field-control">
            <span>Object Type</span>
            <select
              aria-label="Admin object type"
              value={objectType.key}
              onChange={(event) => onSelectObjectType(event.target.value)}
            >
              {data.object_types.map((candidate) => (
                <option key={candidate.key} value={candidate.key}>
                  {candidate.label || candidate.key}
                </option>
              ))}
            </select>
          </label>
        </div>
      </section>
      <ObjectTypeEditor
        objectType={objectType}
        readOnly={readOnly}
        onAddField={addField}
        onChange={(updatedObjectType) =>
          onChange((current) =>
            applyObjectTypeUpdate(current, objectType, updatedObjectType)
          )
        }
        onRemoveField={removeField}
      />
      <FormLayoutEditor
        layout={formLayout}
        objectType={objectType}
        readOnly={readOnly}
        onChange={(updatedLayout) =>
          onChange((current) => ({
            ...current,
            form_layouts: replaceFormLayout(
              current.form_layouts ?? [],
              formLayout.key,
              updatedLayout
            )
          }))
        }
      />
      <FolderTemplateEditor
        template={folderTemplate}
        sampleRecord={sampleRecord}
        readOnly={readOnly}
        onChange={(updatedTemplate) =>
          onChange((current) => ({
            ...current,
            folder_templates: replaceFirst(current.folder_templates ?? [], updatedTemplate)
          }))
        }
      />
      <WorkflowEditor
        workflow={workflow}
        readOnly={readOnly}
        onChange={(updatedWorkflow) =>
          onChange((current) => ({
            ...current,
            workflows: replaceFirst(current.workflows ?? [], updatedWorkflow)
          }))
        }
      />
    </div>
  );
}

function ValidationView({
  errors,
  breakingChanges,
  isValidating,
  hasDraft
}: {
  errors: ValidationError[] | null;
  breakingChanges: ValidationError[];
  isValidating: boolean;
  hasDraft: boolean;
}) {
  const hasBreakingChanges = breakingChanges.length > 0;

  return (
    <section className="table-panel admin-panel" aria-labelledby="validation-title">
      <div className="panel-heading">
        <div>
          <p className="section-kicker">Validation results</p>
          <h2 id="validation-title">Draft Validation</h2>
        </div>
        <StatusBadge
          tone={errors?.length ? "blocked" : hasBreakingChanges ? "review" : errors ? "ready" : "neutral"}
        >
          {validationStatusLabel(errors, breakingChanges)}
        </StatusBadge>
      </div>
      <div className="admin-panel-body">
        {isValidating && <p className="admin-muted">Checking draft configuration.</p>}
        {!hasDraft && <p className="admin-muted">Create a draft before validation.</p>}
        {hasDraft && errors === null && !isValidating && (
          <p className="admin-muted">Run validation to check the draft before publishing.</p>
        )}
        {errors?.length === 0 && (
          <div className="validation-success">
            <CheckCircle2 aria-hidden="true" size={18} />
            No validation errors.
          </div>
        )}
        {hasBreakingChanges && (
          <div className="validation-list" role="list" aria-label="Breaking schema changes">
            {breakingChanges.map((change) => (
              <div className="validation-item validation-warning" role="listitem" key={`${change.path}-${change.code}`}>
                <strong>{change.path || "configuration"}</strong>
                <span>{change.message}</span>
              </div>
            ))}
          </div>
        )}
        {errors && errors.length > 0 && (
          <div className="validation-list" role="list" aria-label="Validation errors">
            {errors.map((error) => (
              <div className="validation-item" role="listitem" key={`${error.path}-${error.code}`}>
                <strong>{error.path || "configuration"}</strong>
                <span>{error.message}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

function PublishView({
  draft,
  validationPassed,
  breakingChanges,
  breakingChangeConfirmed,
  isPublishing,
  onValidate,
  onPublish,
  onBreakingChangeConfirmed
}: {
  draft: ConfigDraft | null;
  validationPassed: boolean;
  breakingChanges: ValidationError[];
  breakingChangeConfirmed: boolean;
  isPublishing: boolean;
  onValidate: () => void;
  onPublish: () => void;
  onBreakingChangeConfirmed: (confirmed: boolean) => void;
}) {
  const hasBreakingChanges = breakingChanges.length > 0;
  const publishDisabled =
    !draft || !validationPassed || isPublishing || (hasBreakingChanges && !breakingChangeConfirmed);

  return (
    <section className="table-panel admin-panel" aria-labelledby="publish-title">
      <div className="panel-heading">
        <div>
          <p className="section-kicker">Publish action</p>
          <h2 id="publish-title">Release Configuration</h2>
        </div>
        <StatusBadge tone={validationPassed ? "ready" : "review"}>
          {validationPassed ? "Ready" : "Needs Validation"}
        </StatusBadge>
      </div>
      <div className="admin-panel-body publish-actions">
        <DefinitionList
          items={[
            ["Draft", draft ? `#${draft.id}` : "None"],
            ["Status", draft?.status ?? "No draft"],
            ["Validation", validationPassed ? "Passed" : "Required"],
            ["Breaking changes", hasBreakingChanges ? breakingChanges.length.toString() : "None"]
          ]}
        />
        {hasBreakingChanges && (
          <div className="admin-alert" role="alert">
            <AlertTriangle aria-hidden="true" size={18} />
            <div>
              <strong>System Admin confirmation required</strong>
              <div className="validation-list" role="list" aria-label="Breaking changes to confirm">
                {breakingChanges.map((change) => (
                  <div className="validation-item validation-warning" role="listitem" key={`${change.path}-${change.code}`}>
                    <strong>{change.path || "configuration"}</strong>
                    <span>{change.message}</span>
                  </div>
                ))}
              </div>
              <label className="toggle-control breaking-change-confirmation">
                <input
                  type="checkbox"
                  checked={breakingChangeConfirmed}
                  disabled={!draft}
                  onChange={(event) => onBreakingChangeConfirmed(event.target.checked)}
                />
                <span>I understand this can hide or invalidate existing record data</span>
              </label>
            </div>
          </div>
        )}
        <div className="admin-button-row">
          <button
            className="button button-secondary"
            type="button"
            onClick={onValidate}
            disabled={!draft}
          >
            <FileCheck2 aria-hidden="true" size={16} />
            Validate Draft
          </button>
          <button
            className="button button-primary"
            type="button"
            onClick={onPublish}
            disabled={publishDisabled}
          >
            <Rocket aria-hidden="true" size={16} />
            Publish Configuration
          </button>
        </div>
      </div>
    </section>
  );
}

function PublishHistoryView({ history }: { history: ConfigVersion[] }) {
  return (
    <section className="table-panel admin-panel" aria-labelledby="history-title">
      <div className="panel-heading">
        <div>
          <p className="section-kicker">Publish history</p>
          <h2 id="history-title">Configuration Versions</h2>
        </div>
        <StatusBadge tone="active">{history.length} Versions</StatusBadge>
      </div>
      <div className="history-list" role="list" aria-label="Publish history">
        {history.map((item) => (
          <div className="history-item" role="listitem" key={item.id}>
            <div>
              <strong>v{item.version}</strong>
              <span>{formatDateTime(item.published_at)}</span>
            </div>
            <StatusBadge tone="ready">Published</StatusBadge>
          </div>
        ))}
      </div>
    </section>
  );
}

function DefinitionList({ items }: { items: Array<[string, string]> }) {
  return (
    <dl className="definition-list">
      {items.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}

const workspaceTabs: Array<{
  value: WorkspaceView;
  label: string;
  icon: typeof ShieldCheck;
}> = [
  { value: "current", label: "Current", icon: ShieldCheck },
  { value: "draft", label: "Draft Editor", icon: Save },
  { value: "validation", label: "Validation", icon: FileCheck2 },
  { value: "publish", label: "Publish", icon: Rocket },
  { value: "history", label: "History", icon: History }
];

function normalizeConfigData(data: ConfigData): ConfigData {
  return {
    ...data,
    object_types: data.object_types ?? [],
    form_layouts: data.form_layouts ?? [],
    folder_templates: data.folder_templates ?? [],
    workflows: data.workflows ?? [],
    relationship_types: data.relationship_types ?? [],
    dashboards: data.dashboards ?? []
  };
}

function replaceFirst<T>(items: T[], value: T) {
  return items.length > 0 ? [value, ...items.slice(1)] : [value];
}

function replaceObjectType(
  items: ObjectTypeDefinition[],
  previousKey: string,
  value: ObjectTypeDefinition
) {
  const index = items.findIndex((item) => item.key === previousKey);
  if (index === -1) {
    return [...items, value];
  }
  return [...items.slice(0, index), value, ...items.slice(index + 1)];
}

function findFormLayout(layouts: FormLayoutDefinition[], objectTypeKey: string) {
  return layouts.find((layout) => layout.object_type_key === objectTypeKey);
}

function replaceFormLayout(
  layouts: FormLayoutDefinition[],
  previousKey: string,
  value: FormLayoutDefinition
) {
  const index = layouts.findIndex(
    (layout) => layout.key === previousKey || layout.object_type_key === previousKey
  );
  if (index === -1) {
    return [...layouts, value];
  }
  return [...layouts.slice(0, index), value, ...layouts.slice(index + 1)];
}

function defaultFieldDefinition(existingFields: FieldDefinition[]): FieldDefinition {
  const fieldKey = nextFieldKey(existingFields);

  return {
    key: fieldKey,
    label: "New Field",
    type: "text",
    required: false,
    searchable: false,
    unique: false
  };
}

function nextFieldKey(existingFields: FieldDefinition[]) {
  const existingKeys = new Set(existingFields.map((field) => field.key));

  if (!existingKeys.has("new_field")) {
    return "new_field";
  }

  let index = 2;
  while (existingKeys.has(`new_field_${index}`)) {
    index += 1;
  }

  return `new_field_${index}`;
}

function addFieldToFirstLayoutSection(
  layout: FormLayoutDefinition,
  fieldKey: string,
  objectTypeKey: string
): FormLayoutDefinition {
  const sections =
    layout.sections && layout.sections.length > 0
      ? layout.sections
      : [{ label: "Identity", fields: [] }];

  return {
    ...layout,
    object_type_key: layout.object_type_key ?? objectTypeKey,
    sections: sections.map((section, index) =>
      index === 0
        ? {
            ...section,
            fields: section.fields.includes(fieldKey)
              ? section.fields
              : [...section.fields, fieldKey]
          }
        : section
    )
  };
}

function removeFieldFromLayouts(
  layouts: FormLayoutDefinition[],
  objectTypeKey: string,
  fieldKey: string
) {
  return layouts.map((layout) => ({
    ...layout,
    sections:
      layout.object_type_key === objectTypeKey
        ? (layout.sections ?? []).map((section) => ({
            ...section,
            fields: section.fields.filter((existingFieldKey) => existingFieldKey !== fieldKey)
          }))
        : layout.sections
  }));
}

function applyObjectTypeUpdate(
  data: ConfigData,
  previousObjectType: ObjectTypeDefinition,
  updatedObjectType: ObjectTypeDefinition
) {
  const renameMap = fieldRenameMap(previousObjectType.fields, updatedObjectType.fields);
  for (const [fromKey, toKey] of inferredLayoutRenameMap(
    data.form_layouts ?? [],
    previousObjectType.key,
    updatedObjectType.fields
  )) {
    renameMap.set(fromKey, toKey);
  }
  const renamedLayouts = renameMap.size
    ? renameFieldsInLayouts(
        data.form_layouts ?? [],
        previousObjectType.key,
        renameMap
      )
    : data.form_layouts ?? [];

  return {
    ...data,
    object_types: replaceObjectType(
      data.object_types,
      previousObjectType.key,
      updatedObjectType
    ),
    form_layouts: renamedLayouts.map((layout) =>
      layout.object_type_key === previousObjectType.key
        ? { ...layout, object_type_key: updatedObjectType.key }
        : layout
    )
  };
}

function inferredLayoutRenameMap(
  layouts: FormLayoutDefinition[],
  objectTypeKey: string,
  updatedFields: FieldDefinition[]
) {
  const updatedFieldKeys = new Set(
    updatedFields.map((field) => field.key).filter(Boolean)
  );
  const layoutFieldKeys = uniqueLayoutFieldKeys(layouts, objectTypeKey);
  const staleLayoutKeys = layoutFieldKeys.filter((fieldKey) => !updatedFieldKeys.has(fieldKey));
  const missingUpdatedKeys = [...updatedFieldKeys].filter(
    (fieldKey) => !layoutFieldKeys.includes(fieldKey)
  );

  if (staleLayoutKeys.length === 1 && missingUpdatedKeys.length === 1) {
    return new Map([[staleLayoutKeys[0], missingUpdatedKeys[0]]]);
  }
  return new Map<string, string>();
}

function fieldRenameMap(
  previousFields: FieldDefinition[],
  updatedFields: FieldDefinition[]
) {
  const renames = new Map<string, string>();
  updatedFields.forEach((updatedField, index) => {
    const previousField = previousFields[index];
    if (
      previousField?.key &&
      updatedField.key &&
      previousField.key !== updatedField.key
    ) {
      renames.set(previousField.key, updatedField.key);
    }
  });
  return renames;
}

function uniqueLayoutFieldKeys(layouts: FormLayoutDefinition[], objectTypeKey: string) {
  const keys: string[] = [];
  layouts
    .filter((layout) => layout.object_type_key === objectTypeKey)
    .forEach((layout) => {
      (layout.sections ?? []).forEach((section) => {
        section.fields.forEach((fieldKey) => {
          if (!keys.includes(fieldKey)) {
            keys.push(fieldKey);
          }
        });
      });
    });
  return keys;
}

function renameFieldsInLayouts(
  layouts: FormLayoutDefinition[],
  objectTypeKey: string,
  renameMap: Map<string, string>
) {
  return layouts.map((layout) => ({
    ...layout,
    sections:
      layout.object_type_key === objectTypeKey
        ? (layout.sections ?? []).map((section) => ({
            ...section,
            fields: section.fields.map((fieldKey) => renameMap.get(fieldKey) ?? fieldKey)
          }))
        : layout.sections
  }));
}

function mergeHistory(history: ConfigVersion[], version: ConfigVersion) {
  return [version, ...history.filter((item) => item.id !== version.id)].sort(
    (first, second) => second.version - first.version
  );
}

function validationStatusLabel(errors: ValidationError[] | null, breakingChanges: ValidationError[] = []) {
  if (errors === null) {
    return "Not checked";
  }

  if (errors.length > 0) {
    return `${errors.length} errors`;
  }

  if (breakingChanges.length > 0) {
    return `${breakingChanges.length} breaking changes`;
  }

  return "No validation errors";
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Configuration request failed.";
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

function defaultObjectType(): ObjectTypeDefinition {
  return {
    key: "product",
    label: "Product",
    plural_label: "Products",
    code_pattern: "PROD-{seq:000000}",
    title_field: "commercial_name",
    fields: [
      {
        key: "commercial_name",
        label: "Commercial Name",
        type: "text",
        required: true
      }
    ]
  };
}

function defaultFormLayout(objectTypeKey: string): FormLayoutDefinition {
  return {
    key: `${objectTypeKey}_release`,
    object_type_key: objectTypeKey,
    sections: [{ label: "Identity", fields: ["commercial_name"] }]
  };
}

function defaultFolderTemplate(key?: string): FolderTemplateDefinition {
  return {
    key: key ?? "product_standard",
    label: "Product Standard",
    pattern: "/Products/{code}-{commercial_name}/Release"
  };
}

function defaultWorkflow(key?: string): WorkflowDefinition {
  return {
    key: key ?? "engineering_release",
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
  };
}
