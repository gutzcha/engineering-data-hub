/*
 * ===
 * File Summary
 * Path: frontend\src\features\admin-config\ObjectTypeEditor.tsx
 * Type: typescript
 * Purpose: Frontend feature module implementing business flows and UI surfaces.
 * Primary responsibilities:
 * - Domain behavior is summarized for fast onboarding and avoids full-file reread.
 * - Core symbols: ObjectTypeEditor
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

import type { ObjectTypeDefinition } from "./ConfigWorkspace";
import { FieldEditor } from "./FieldEditor";

type ObjectTypeEditorProps = {
  objectType: ObjectTypeDefinition;
  readOnly: boolean;
  onChange: (objectType: ObjectTypeDefinition) => void;
};

export function ObjectTypeEditor({
  objectType,
  readOnly,
  onChange
}: ObjectTypeEditorProps) {
  function updateField<Key extends keyof ObjectTypeDefinition>(
    key: Key,
    value: ObjectTypeDefinition[Key]
  ) {
    onChange({ ...objectType, [key]: value });
  }

  return (
    <section className="table-panel admin-panel" aria-labelledby="object-type-title">
      <div className="panel-heading">
        <div>
          <p className="section-kicker">Object type and fields</p>
          <h2 id="object-type-title">Object Type Editor</h2>
        </div>
      </div>
      <div className="admin-panel-body editor-stack">
        <div className="admin-form-grid">
          <label className="field-control">
            <span>Object key</span>
            <input
              value={objectType.key}
              disabled={readOnly}
              onChange={(event) => updateField("key", event.target.value)}
            />
          </label>
          <label className="field-control">
            <span>Label</span>
            <input
              value={objectType.label}
              disabled={readOnly}
              onChange={(event) => updateField("label", event.target.value)}
            />
          </label>
          <label className="field-control">
            <span>Plural label</span>
            <input
              value={objectType.plural_label ?? ""}
              disabled={readOnly}
              onChange={(event) => updateField("plural_label", event.target.value)}
            />
          </label>
          <label className="field-control">
            <span>Code pattern</span>
            <input
              value={objectType.code_pattern ?? ""}
              disabled={readOnly}
              onChange={(event) => updateField("code_pattern", event.target.value)}
            />
          </label>
          <label className="field-control">
            <span>Title field</span>
            <input
              value={objectType.title_field ?? ""}
              disabled={readOnly}
              onChange={(event) => updateField("title_field", event.target.value)}
            />
          </label>
        </div>

        <div className="field-list" aria-label="Field list">
          {objectType.fields.map((field, index) => (
            <FieldEditor
              key={field.key || index}
              field={field}
              readOnly={readOnly}
              onChange={(updatedField) => {
                const fields = [...objectType.fields];
                fields[index] = updatedField;
                updateField("fields", fields);
              }}
            />
          ))}
        </div>
      </div>
    </section>
  );
}

