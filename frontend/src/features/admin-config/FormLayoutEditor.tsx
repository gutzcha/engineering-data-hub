import type { FormLayoutDefinition, ObjectTypeDefinition } from "./ConfigWorkspace";

type FormLayoutEditorProps = {
  layout: FormLayoutDefinition;
  objectType: ObjectTypeDefinition;
  readOnly: boolean;
  onChange: (layout: FormLayoutDefinition) => void;
};

export function FormLayoutEditor({
  layout,
  objectType,
  readOnly,
  onChange
}: FormLayoutEditorProps) {
  const firstSection = layout.sections?.[0] ?? { label: "Identity", fields: [] };

  function updateFirstSection(section: typeof firstSection) {
    const sections = layout.sections?.length
      ? [section, ...layout.sections.slice(1)]
      : [section];
    onChange({ ...layout, sections });
  }

  return (
    <section className="table-panel admin-panel" aria-labelledby="form-layout-title">
      <div className="panel-heading">
        <div>
          <p className="section-kicker">Record entry</p>
          <h2 id="form-layout-title">Form Layout Editor</h2>
        </div>
      </div>
      <div className="admin-panel-body editor-stack">
        <div className="admin-form-grid">
          <label className="field-control">
            <span>Layout key</span>
            <input
              value={layout.key}
              disabled={readOnly}
              onChange={(event) => onChange({ ...layout, key: event.target.value })}
            />
          </label>
          <label className="field-control">
            <span>Object type</span>
            <input
              value={layout.object_type_key ?? objectType.key}
              disabled={readOnly}
              onChange={(event) =>
                onChange({ ...layout, object_type_key: event.target.value })
              }
            />
          </label>
          <label className="field-control">
            <span>Section label</span>
            <input
              value={firstSection.label}
              disabled={readOnly}
              onChange={(event) =>
                updateFirstSection({ ...firstSection, label: event.target.value })
              }
            />
          </label>
          <label className="field-control">
            <span>Visible fields</span>
            <input
              value={firstSection.fields.join(", ")}
              disabled={readOnly}
              onChange={(event) =>
                updateFirstSection({
                  ...firstSection,
                  fields: splitList(event.target.value)
                })
              }
            />
          </label>
        </div>
        <div className="layout-preview" aria-label="Form layout preview">
          <strong>{firstSection.label}</strong>
          <div>
            {firstSection.fields.map((fieldKey) => {
              const field = objectType.fields.find((candidate) => candidate.key === fieldKey);
              return <span key={fieldKey}>{field?.label ?? fieldKey}</span>;
            })}
          </div>
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
