/*
 * ===
 * File Summary
 * Path: frontend\src\features\dashboards\SavedViewBuilder.tsx
 * Type: typescript
 * Purpose: Frontend feature module implementing business flows and UI surfaces.
 * Primary responsibilities:
 * - Domain behavior is summarized for fast onboarding and avoids full-file reread.
 * - Core symbols: DashboardObjectType, SavedView, SavedViewDraft, SavedViewBuilder
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

import { Loader2, PlayCircle, Save } from "lucide-react";
import { useState } from "react";

import { StatusBadge } from "../../components/StatusBadge";

export type DashboardObjectType = {
  key: string;
  label?: string;
  plural_label?: string;
  fields?: Array<{ key: string; label?: string }>;
};

export type SavedView = {
  id: string | number;
  name: string;
  filters?: Array<Record<string, unknown>>;
  columns?: string[];
  sort?: string[];
  created_at?: string;
  updated_at?: string;
};

export type SavedViewDraft = {
  name: string;
  filters: Array<Record<string, unknown>>;
  columns: string[];
  sort: string[];
};

type SavedViewBuilderProps = {
  objectTypes: DashboardObjectType[];
  savedViews: SavedView[];
  selectedSavedViewId: string;
  isSaving?: boolean;
  isRunning?: boolean;
  onCreate: (draft: SavedViewDraft) => void;
  onRun: () => void;
  onSelectSavedView: (savedViewId: string) => void;
};

export function SavedViewBuilder({
  objectTypes,
  savedViews,
  selectedSavedViewId,
  isRunning = false,
  isSaving = false,
  onCreate,
  onRun,
  onSelectSavedView
}: SavedViewBuilderProps) {
  const [name, setName] = useState("");
  const [objectType, setObjectType] = useState("");
  const [status, setStatus] = useState("");
  const [columns, setColumns] = useState("code, title, status");

  function saveView() {
    const filters: Array<Record<string, unknown>> = [];
    if (objectType) {
      filters.push({ type: "object_type", value: objectType });
    }
    if (status) {
      filters.push({ type: "status", value: status });
    }

    onCreate({
      name: name.trim() || "Untitled Saved View",
      filters,
      columns: splitList(columns),
      sort: ["code"]
    });
  }

  return (
    <section className="table-panel saved-view-builder" aria-labelledby="saved-view-title">
      <div className="panel-heading">
        <div>
          <p className="section-kicker">Saved list views</p>
          <h2 id="saved-view-title">Saved Views</h2>
        </div>
        <StatusBadge tone={savedViews.length ? "active" : "neutral"}>
          {savedViews.length} Views
        </StatusBadge>
      </div>
      <div className="record-panel-body">
        <div className="saved-view-runner">
          <label className="field-control">
            <span>Saved View</span>
            <select
              aria-label="Saved view"
              value={selectedSavedViewId}
              onChange={(event) => onSelectSavedView(event.target.value)}
            >
              <option value="">Choose view</option>
              {savedViews.map((view) => (
                <option key={view.id} value={String(view.id)}>
                  {view.name}
                </option>
              ))}
            </select>
          </label>
          <button
            className="button button-secondary"
            type="button"
            onClick={onRun}
            disabled={!selectedSavedViewId || isRunning}
          >
            {isRunning ? (
              <Loader2 aria-hidden="true" size={16} />
            ) : (
              <PlayCircle aria-hidden="true" size={16} />
            )}
            Run Saved View
          </button>
        </div>

        <div className="admin-form-grid" aria-label="Saved view builder">
          <label className="field-control">
            <span>View Name</span>
            <input
              aria-label="View name"
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </label>
          <label className="field-control">
            <span>Object Type</span>
            <select
              aria-label="Saved view object type"
              value={objectType}
              onChange={(event) => setObjectType(event.target.value)}
            >
              <option value="">Any object type</option>
              {objectTypes.map((item) => (
                <option key={item.key} value={item.key}>
                  {item.label ?? item.key}
                </option>
              ))}
            </select>
          </label>
          <label className="field-control">
            <span>Status</span>
            <select
              aria-label="Saved view status"
              value={status}
              onChange={(event) => setStatus(event.target.value)}
            >
              <option value="">Any status</option>
              <option value="draft">Draft</option>
              <option value="released">Released</option>
              <option value="blocked">Blocked</option>
            </select>
          </label>
          <label className="field-control">
            <span>Columns</span>
            <input
              aria-label="Saved view columns"
              value={columns}
              onChange={(event) => setColumns(event.target.value)}
            />
          </label>
        </div>
        <div className="admin-button-row">
          <button
            className="button button-secondary"
            type="button"
            onClick={saveView}
            disabled={isSaving}
          >
            {isSaving ? (
              <Loader2 aria-hidden="true" size={16} />
            ) : (
              <Save aria-hidden="true" size={16} />
            )}
            Save View
          </button>
        </div>
      </div>
    </section>
  );
}

function splitList(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

