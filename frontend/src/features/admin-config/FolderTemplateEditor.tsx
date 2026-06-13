/*
 * ===
 * File Summary
 * Path: frontend\src\features\admin-config\FolderTemplateEditor.tsx
 * Type: typescript
 * Purpose: Frontend feature module implementing business flows and UI surfaces.
 * Primary responsibilities:
 * - Domain behavior is summarized for fast onboarding and avoids full-file reread.
 * - Core symbols: FolderTemplateEditor
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

import type { FolderTemplateDefinition } from "./ConfigWorkspace";

type FolderTemplateEditorProps = {
  template: FolderTemplateDefinition;
  sampleRecord: Record<string, string>;
  readOnly: boolean;
  onChange: (template: FolderTemplateDefinition) => void;
};

export function FolderTemplateEditor({
  template,
  sampleRecord,
  readOnly,
  onChange
}: FolderTemplateEditorProps) {
  const renderedPath = renderPath(template.pattern, sampleRecord);

  return (
    <section className="table-panel admin-panel" aria-labelledby="folder-template-title">
      <div className="panel-heading">
        <div>
          <p className="section-kicker">Controlled folders</p>
          <h2 id="folder-template-title">Folder Template Editor</h2>
        </div>
      </div>
      <div className="admin-panel-body editor-stack">
        <div className="admin-form-grid">
          <label className="field-control">
            <span>Template key</span>
            <input
              value={template.key}
              disabled={readOnly}
              onChange={(event) => onChange({ ...template, key: event.target.value })}
            />
          </label>
          <label className="field-control">
            <span>Template label</span>
            <input
              value={template.label ?? ""}
              disabled={readOnly}
              onChange={(event) => onChange({ ...template, label: event.target.value })}
            />
          </label>
          <label className="field-control field-control-wide">
            <span>Path pattern</span>
            <input
              value={template.pattern}
              disabled={readOnly}
              onChange={(event) =>
                onChange({ ...template, pattern: event.target.value })
              }
            />
          </label>
        </div>
        <div className="path-preview" aria-label="Rendered folder path preview">
          <span>Sample rendered path</span>
          <strong>{renderedPath}</strong>
        </div>
      </div>
    </section>
  );
}

function renderPath(pattern: string, sampleRecord: Record<string, string>) {
  return pattern.replace(/\{([a-zA-Z0-9_]+)\}/g, (_match, key: string) => {
    return sampleRecord[key] ?? `{${key}}`;
  });
}

