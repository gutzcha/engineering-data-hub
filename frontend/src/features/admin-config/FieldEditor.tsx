import type { FieldDefinition } from "./ConfigWorkspace";

type FieldEditorProps = {
  field: FieldDefinition;
  readOnly: boolean;
  onChange: (field: FieldDefinition) => void;
};

const fieldTypes = [
  "text",
  "long_text",
  "number",
  "date",
  "boolean",
  "choice",
  "multi_choice",
  "record_ref",
  "file_ref",
  "url",
  "user_ref"
];

export function FieldEditor({ field, readOnly, onChange }: FieldEditorProps) {
  function updateField<Key extends keyof FieldDefinition>(
    key: Key,
    value: FieldDefinition[Key]
  ) {
    onChange({ ...field, [key]: value });
  }

  return (
    <article className="field-editor">
      <div className="field-editor-main">
        <label className="field-control">
          <span>Field key</span>
          <input
            value={field.key}
            disabled={readOnly}
            onChange={(event) => updateField("key", event.target.value)}
          />
        </label>
        <label className="field-control">
          <span>Field label</span>
          <input
            value={field.label}
            disabled={readOnly}
            onChange={(event) => updateField("label", event.target.value)}
          />
        </label>
        <label className="field-control">
          <span>Field type</span>
          <select
            value={field.type}
            disabled={readOnly}
            onChange={(event) => updateField("type", event.target.value)}
          >
            {fieldTypes.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="toggle-row" aria-label={`${field.label} field controls`}>
        <label className="toggle-control">
          <input
            type="checkbox"
            checked={Boolean(field.required)}
            disabled={readOnly}
            onChange={(event) => updateField("required", event.target.checked)}
          />
          <span>{field.label} required</span>
        </label>
        <label className="toggle-control">
          <input
            type="checkbox"
            checked={Boolean(field.searchable)}
            disabled={readOnly}
            onChange={(event) => updateField("searchable", event.target.checked)}
          />
          <span>{field.label} searchable</span>
        </label>
        <label className="toggle-control">
          <input
            type="checkbox"
            checked={Boolean(field.unique)}
            disabled={readOnly}
            onChange={(event) => updateField("unique", event.target.checked)}
          />
          <span>{field.label} unique</span>
        </label>
      </div>

      {(field.type === "choice" || field.type === "multi_choice") && (
        <label className="field-control">
          <span>{field.label} choice options</span>
          <input
            value={(field.options ?? []).join(", ")}
            disabled={readOnly}
            onChange={(event) =>
              updateField(
                "options",
                event.target.value
                  .split(",")
                  .map((option) => option.trim())
                  .filter(Boolean)
              )
            }
          />
        </label>
      )}

      {field.type === "record_ref" && (
        <label className="field-control">
          <span>{field.label} reference target type</span>
          <input
            value={field.reference_target_type ?? ""}
            disabled={readOnly}
            onChange={(event) =>
              updateField("reference_target_type", event.target.value)
            }
          />
        </label>
      )}
    </article>
  );
}
