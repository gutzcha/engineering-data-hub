/*
 * ===
 * File Summary
 * Path: frontend\src\features\imports\ImportWizard.tsx
 * Type: typescript
 * Purpose: Frontend feature module implementing business flows and UI surfaces.
 * Primary responsibilities:
 * - Domain behavior is summarized for fast onboarding and avoids full-file reread.
 * - Core symbols: ImportWizard
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

import { useMutation, useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  FileSpreadsheet,
  Loader2,
  PlayCircle,
  Upload
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { DataTable } from "../../components/DataTable";
import { StatusBadge } from "../../components/StatusBadge";
import { apiGet, apiPost, apiPostForm } from "../../lib/api";

type FieldDefinition = {
  key: string;
  label?: string;
  required?: boolean;
  type?: string;
};

type ObjectTypeDefinition = {
  key: string;
  label?: string;
  plural_label?: string;
  fields?: FieldDefinition[];
};

type ConfigVersion = {
  data?: {
    object_types?: ObjectTypeDefinition[];
  };
};

type ImportJob = {
  id: string | number;
  target_object_type: string;
  mapping?: ImportMapping;
  state?: string;
};

type ImportMapping = {
  columns: Record<string, string>;
};

type ImportDryRunResult = {
  summary: {
    create: number;
    update: number;
    errors: number;
  };
  creates?: ImportPreviewRow[];
  updates?: ImportPreviewRow[];
  error_rows?: ImportErrorRow[];
};

type ImportPreviewRow = {
  row_number: number;
  code?: string;
  data?: Record<string, unknown>;
  record_id?: string | number;
};

type ImportErrorRow = {
  row_number: number;
  code?: string;
  errors: Record<string, string[]>;
};

type ApplyResult = {
  created: number;
  updated: number;
};

type ImportColumnPreviewResponse = {
  columns?: string[];
};

const codeField: FieldDefinition = {
  key: "code",
  label: "Code"
};

export function ImportWizard() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [sourceColumns, setSourceColumns] = useState<string[]>([]);
  const [targetObjectType, setTargetObjectType] = useState("");
  const [fieldMapping, setFieldMapping] = useState<Record<string, string>>({});
  const [job, setJob] = useState<ImportJob | null>(null);
  const [dryRunResult, setDryRunResult] = useState<ImportDryRunResult | null>(null);
  const [applyResult, setApplyResult] = useState<ApplyResult | null>(null);
  const [createManagedFolders, setCreateManagedFolders] = useState(false);
  const [localError, setLocalError] = useState("");
  const [isPreviewLoading, setIsPreviewLoading] = useState(false);

  const configQuery = useQuery({
    queryKey: ["config", "active"],
    queryFn: () => apiGet<ConfigVersion>("/config/active/")
  });

  const objectTypes = configQuery.data?.data?.object_types ?? [];
  const selectedObjectType = objectTypes.find((objectType) => objectType.key === targetObjectType);
  const targetFields = useMemo(
    () => [codeField, ...(selectedObjectType?.fields ?? [])],
    [selectedObjectType?.fields]
  );
  const hasDryRunErrors = (dryRunResult?.summary.errors ?? 0) > 0;

  useEffect(() => {
    if (!targetObjectType && objectTypes[0]) {
      setTargetObjectType(objectTypes[0].key);
    }
  }, [objectTypes, targetObjectType]);

  useEffect(() => {
    setFieldMapping((current) => autoMapping(targetFields, sourceColumns, current));
  }, [sourceColumns, targetFields]);

  const dryRunImport = useMutation({
    mutationFn: async () => {
      setLocalError("");
      if (!selectedFile) {
        throw new Error("Choose a source file before running dry-run.");
      }
      if (!targetObjectType) {
        throw new Error("Choose an object type before running dry-run.");
      }

      const formData = new FormData();
      formData.append("target_object_type", targetObjectType);
      formData.append("source_file", selectedFile);
      formData.append("mapping", JSON.stringify(buildImportMapping(fieldMapping)));
      const createdJob = await apiPostForm<ImportJob>("/imports/jobs/", formData);
      const result = await apiPost<ImportDryRunResult>(
        `/imports/jobs/${createdJob.id}/dry-run/`,
        {}
      );
      setJob(createdJob);
      setDryRunResult(result);
      setApplyResult(null);
      return result;
    },
    onError: (error) => {
      setLocalError(errorMessage(error));
    }
  });

  const applyImport = useMutation({
    mutationFn: async () => {
      if (!job) {
        throw new Error("Run a clean dry-run before applying the import.");
      }
      return apiPost<ApplyResult>(`/imports/jobs/${job.id}/apply/`, {
        create_managed_folders: createManagedFolders
      });
    },
    onSuccess: (result) => {
      setApplyResult(result);
    },
    onError: (error) => {
      setLocalError(errorMessage(error));
    }
  });

async function updateSourceFile(file?: File) {
    setSelectedFile(file ?? null);
    setDryRunResult(null);
    setApplyResult(null);
    setJob(null);
    setLocalError("");
    if (!file) {
      setSourceColumns([]);
      return;
    }

    setIsPreviewLoading(true);
    try {
      setSourceColumns(await columnsFromFile(file));
    } catch (error) {
      setLocalError(errorMessage(error));
      setSourceColumns([]);
    } finally {
      setIsPreviewLoading(false);
    }
  }

  return (
    <div className="page-stack import-page">
      <section className="workspace-header" aria-labelledby="import-wizard-title">
        <div>
          <p className="section-kicker">Excel and CSV intake</p>
          <h1 id="import-wizard-title">Import Wizard</h1>
        </div>
        <StatusBadge tone={dryRunResult ? (hasDryRunErrors ? "blocked" : "ready") : "neutral"}>
          {dryRunResult ? "Dry-run complete" : "Draft mapping"}
        </StatusBadge>
      </section>

      {(localError || configQuery.error) && (
        <div className="admin-alert" role="alert">
          <strong>Import action failed</strong>
          <span>{localError || errorMessage(configQuery.error)}</span>
        </div>
      )}

      <section className="filter-panel" aria-label="Import setup">
        <div className="import-setup-grid">
          <label className="upload-control">
            <Upload aria-hidden="true" size={16} />
            <span>{selectedFile?.name ?? "Source file"}</span>
            <input
              aria-label="Source file"
              type="file"
              accept=".csv,.xlsx,.xls,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              onChange={(event) => void updateSourceFile(event.target.files?.[0])}
            />
          </label>
          <label className="field-control">
            <span>Object Type</span>
            <select
              aria-label="Object type"
              value={targetObjectType}
              onChange={(event) => {
                setTargetObjectType(event.target.value);
                setDryRunResult(null);
                setApplyResult(null);
                setJob(null);
              }}
            >
              {objectTypes.length === 0 && <option value="">Loading object types</option>}
              {objectTypes.map((objectType) => (
                <option key={objectType.key} value={objectType.key}>
                  {objectType.label ?? objectType.key}
                </option>
              ))}
            </select>
          </label>
          <label className="toggle-control import-folder-toggle">
            <input
              aria-label="Create managed folders"
              type="checkbox"
              checked={createManagedFolders}
              onChange={(event) => setCreateManagedFolders(event.target.checked)}
            />
            Create managed folders
          </label>
        </div>
      </section>

      <section className="table-panel" aria-labelledby="mapping-title">
        <div className="panel-heading">
          <div>
            <p className="section-kicker">Column mapping</p>
            <h2 id="mapping-title">Map Columns To Fields</h2>
          </div>
          <StatusBadge tone={sourceColumns.length ? "active" : "neutral"}>
            {sourceColumns.length ? `${sourceColumns.length} Columns` : "Manual"}
          </StatusBadge>
        </div>
        <div className="record-panel-body">
          <div className="mapping-grid">
            {targetFields.map((field) => (
              <ColumnMappingControl
                key={field.key}
                field={field}
                sourceColumns={sourceColumns}
                value={fieldMapping[field.key] ?? ""}
                onChange={(value) => {
                  setFieldMapping((current) => ({ ...current, [field.key]: value }));
                  setDryRunResult(null);
                  setApplyResult(null);
                  setJob(null);
                }}
              />
            ))}
          </div>
          <div className="admin-button-row">
            <button
              className="button button-primary"
              type="button"
              onClick={() => dryRunImport.mutate()}
              disabled={dryRunImport.isPending || configQuery.isLoading}
            >
              {dryRunImport.isPending ? (
                <Loader2 aria-hidden="true" size={16} />
              ) : (
                <PlayCircle aria-hidden="true" size={16} />
              )}
              Run Dry-run
            </button>
            <button
              className="button button-secondary"
              type="button"
              onClick={() => applyImport.mutate()}
              disabled={!dryRunResult || hasDryRunErrors || applyImport.isPending}
            >
              {applyImport.isPending ? (
                <Loader2 aria-hidden="true" size={16} />
              ) : (
                <CheckCircle2 aria-hidden="true" size={16} />
              )}
              Apply Import
            </button>
          </div>
        </div>
      </section>

      {dryRunResult && <DryRunResults result={dryRunResult} />}

      {applyResult && (
        <div className="validation-success">
          <CheckCircle2 aria-hidden="true" size={18} />
          Applied {applyResult.created} created / {applyResult.updated} updated
        </div>
      )}
    </div>
  );
}

function ColumnMappingControl({
  field,
  sourceColumns,
  value,
  onChange
}: {
  field: FieldDefinition;
  sourceColumns: string[];
  value: string;
  onChange: (value: string) => void;
}) {
  const label = `${field.label ?? humanize(field.key)} Source Column`;

  return (
    <label className="field-control">
      <span>
        {field.label ?? humanize(field.key)}
        {field.required ? " *" : ""}
      </span>
      {sourceColumns.length ? (
        <select
          aria-label={label}
          value={value}
          onChange={(event) => onChange(event.target.value)}
        >
          <option value="">Do not import</option>
          {sourceColumns.map((column) => (
            <option key={column} value={column}>
              {column}
            </option>
          ))}
        </select>
      ) : (
        <input
          aria-label={label}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder="Column header"
        />
      )}
    </label>
  );
}

function DryRunResults({ result }: { result: ImportDryRunResult }) {
  const previews = [...(result.creates ?? []), ...(result.updates ?? [])].slice(0, 8);

  return (
    <div className="detail-grid import-results-grid">
      <section className="admin-status-row" aria-label="Import dry-run summary">
        <div className="admin-stat">
          <span>Create</span>
          <strong>{result.summary.create} Create</strong>
        </div>
        <div className="admin-stat">
          <span>Update</span>
          <strong>{result.summary.update} Update</strong>
        </div>
        <div className="admin-stat">
          <span>Errors</span>
          <strong>{result.summary.errors} Error{result.summary.errors === 1 ? "" : "s"}</strong>
        </div>
      </section>

      <section className="table-panel" aria-labelledby="dry-run-errors-title">
        <div className="panel-heading">
          <div>
            <p className="section-kicker">Review errors</p>
            <h2 id="dry-run-errors-title">Dry-run Errors</h2>
          </div>
          <StatusBadge tone={result.summary.errors ? "blocked" : "ready"}>
            {result.summary.errors ? "Fix Required" : "Clean"}
          </StatusBadge>
        </div>
        <div className="record-panel-body">
          {(result.error_rows ?? []).length === 0 ? (
            <div className="validation-success">
              <CheckCircle2 aria-hidden="true" size={18} />
              No import row errors.
            </div>
          ) : (
            <div className="validation-list" role="list" aria-label="Import row errors">
              {(result.error_rows ?? []).map((row) => (
                <div className="validation-item import-error-item" role="listitem" key={row.row_number}>
                  <AlertTriangle aria-hidden="true" size={18} />
                  <div>
                    <strong>Row {row.row_number}</strong>
                    <span>{formatRowErrors(row.errors)}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>

      <section className="table-panel" aria-labelledby="dry-run-preview-title">
        <div className="panel-heading">
          <div>
            <p className="section-kicker">Preview</p>
            <h2 id="dry-run-preview-title">Creates And Updates</h2>
          </div>
          <FileSpreadsheet aria-hidden="true" size={18} />
        </div>
        <DataTable
          data={previews}
          emptyMessage="No clean rows are ready to import."
          columns={[
            {
              accessorKey: "row_number",
              header: "Row"
            },
            {
              accessorKey: "code",
              header: "Code",
              cell: ({ row }) => row.original.code || "Auto"
            },
            {
              id: "data",
              header: "Fields",
              cell: ({ row }) => Object.entries(row.original.data ?? {}).map(([key, value]) => `${key}: ${String(value)}`).join(", ")
            }
          ]}
        />
      </section>
    </div>
  );
}

function buildImportMapping(fieldMapping: Record<string, string>): ImportMapping {
  const columns = Object.entries(fieldMapping).reduce<Record<string, string>>(
    (current, [targetField, sourceColumn]) => {
      const trimmed = sourceColumn.trim();
      if (trimmed) {
        current[trimmed] = targetField;
      }
      return current;
    },
    {}
  );
  return { columns };
}

async function columnsFromFile(file: File) {
  if (file.name.toLowerCase().endsWith(".csv")) {
    const firstLine = (await readFileText(file)).split(/\r?\n/, 1)[0] ?? "";
    return parseCsvLine(firstLine).filter(Boolean);
  }

  const formData = new FormData();
  formData.append("source_file", file);
  const result = await apiPost<ImportColumnPreviewResponse>("/imports/columns-preview/", formData);
  return result.columns ?? [];
}

function readFileText(file: File) {
  const maybeText = (file as File & { text?: () => Promise<string> }).text;
  if (typeof maybeText === "function") {
    return maybeText.call(file);
  }

  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.addEventListener("load", () => resolve(String(reader.result ?? "")));
    reader.addEventListener("error", () => reject(reader.error ?? new Error("File read failed.")));
    reader.readAsText(file);
  });
}

function parseCsvLine(line: string) {
  const values: string[] = [];
  let value = "";
  let quoted = false;
  for (let index = 0; index < line.length; index += 1) {
    const character = line[index];
    if (character === '"' && line[index + 1] === '"') {
      value += '"';
      index += 1;
    } else if (character === '"') {
      quoted = !quoted;
    } else if (character === "," && !quoted) {
      values.push(value.trim());
      value = "";
    } else {
      value += character;
    }
  }
  values.push(value.trim());
  return values;
}

function autoMapping(
  fields: FieldDefinition[],
  sourceColumns: string[],
  current: Record<string, string>
) {
  const next = { ...current };
  for (const field of fields) {
    if (next[field.key]) {
      continue;
    }
    const match = sourceColumns.find((column) => columnMatchesField(column, field));
    if (match) {
      next[field.key] = match;
    }
  }
  return next;
}

function columnMatchesField(column: string, field: FieldDefinition) {
  const normalizedColumn = normalize(column);
  return [field.key, field.label ?? ""].some((value) => normalize(value) === normalizedColumn);
}

function normalize(value: string) {
  return value.replace(/[_\s-]+/g, "").toLowerCase();
}

function formatRowErrors(errors: Record<string, string[]>) {
  return Object.entries(errors)
    .map(([field, messages]) => `${field}: ${messages.join(", ")}`)
    .join(" ");
}

function humanize(value: string) {
  return value.replace(/[_-]+/g, " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Import request failed.";
}

