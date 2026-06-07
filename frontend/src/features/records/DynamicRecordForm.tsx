export type FieldDefinition = {
  key: string;
  label?: string;
  type?: string;
  required?: boolean;
  options?: string[];
  reference_target_type?: string;
};

export type ObjectTypeDefinition = {
  key: string;
  label?: string;
  plural_label?: string;
  title_field?: string;
  fields?: FieldDefinition[];
};

export type FormLayoutDefinition = {
  key: string;
  object_type_key?: string;
  sections?: Array<{
    label?: string;
    fields?: string[];
  }>;
};

export type ConfigData = {
  object_types?: ObjectTypeDefinition[];
  form_layouts?: FormLayoutDefinition[];
};

export type RecordValue = string | number | boolean | string[] | null | undefined;
export type RecordValues = Record<string, RecordValue>;

type DynamicRecordFormProps = {
  config?: ConfigData;
  objectTypeKey?: string;
  values: RecordValues;
  onChange: (values: RecordValues) => void;
  readOnly?: boolean;
};

export function DynamicRecordForm({
  config,
  objectTypeKey,
  values,
  onChange,
  readOnly = false
}: DynamicRecordFormProps) {
  const objectType = findObjectType(config, objectTypeKey);
  const fields = objectType?.fields ?? [];
  const fieldsByKey = new Map(fields.map((field) => [field.key, field]));
  const sections = sectionsForObjectType(config, objectType?.key, fields);

  if (!objectType) {
    return (
      <div className="admin-muted">
        Published configuration for this record type is not available.
      </div>
    );
  }

  return (
    <div className="record-form-stack">
      {sections.map((section) => (
        <section
          className="record-form-section"
          aria-labelledby={`record-form-${section.label}`}
          key={section.label}
        >
          <div className="record-section-heading">
            <h3 id={`record-form-${section.label}`}>{section.label}</h3>
          </div>
          <div className="admin-form-grid">
            {section.fields.map((fieldKey) => {
              const field = fieldsByKey.get(fieldKey);

              return field ? (
                <FieldControl
                  field={field}
                  key={field.key}
                  value={values[field.key]}
                  readOnly={readOnly}
                  onChange={(value) => onChange({ ...values, [field.key]: value })}
                />
              ) : null;
            })}
          </div>
        </section>
      ))}
    </div>
  );
}

function FieldControl({
  field,
  value,
  readOnly,
  onChange
}: {
  field: FieldDefinition;
  value: RecordValue;
  readOnly: boolean;
  onChange: (value: RecordValue) => void;
}) {
  const label = field.label ?? humanize(field.key);
  const type = field.type ?? "text";

  if (type === "boolean") {
    return (
      <label className="toggle-control record-toggle">
        <input
          type="checkbox"
          checked={Boolean(value)}
          disabled={readOnly}
          onChange={(event) => onChange(event.target.checked)}
        />
        {label}
      </label>
    );
  }

  if (type === "multi_choice") {
    const selectedValues = Array.isArray(value) ? value : [];

    return (
      <label className="field-control">
        <span>
          {label}
          {field.required ? " *" : ""}
        </span>
        <select
          aria-label={label}
          value={selectedValues}
          disabled={readOnly}
          required={field.required}
          multiple
          onChange={(event) =>
            onChange(
              Array.from(event.target.selectedOptions).map((option) => option.value)
            )
          }
        >
          {(field.options ?? []).map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </label>
    );
  }

  if (type === "choice" || field.options?.length) {
    return (
      <label className="field-control">
        <span>
          {label}
          {field.required ? " *" : ""}
        </span>
        <select
          aria-label={label}
          value={stringValue(value)}
          disabled={readOnly}
          required={field.required}
          onChange={(event) => onChange(event.target.value)}
        >
          <option value="">Select</option>
          {(field.options ?? []).map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </label>
    );
  }

  if (type === "long_text" || type === "textarea" || type === "json") {
    return (
      <label className="field-control field-control-wide">
        <span>
          {label}
          {field.required ? " *" : ""}
        </span>
        <textarea
          aria-label={label}
          value={stringValue(value)}
          disabled={readOnly}
          required={field.required}
          rows={4}
          onChange={(event) => onChange(event.target.value)}
        />
      </label>
    );
  }

  return (
    <label className="field-control">
      <span>
        {label}
        {field.required ? " *" : ""}
      </span>
      <input
        aria-label={label}
        type={inputType(type)}
        value={stringValue(value)}
        disabled={readOnly}
        required={field.required}
        onChange={(event) =>
          onChange(type === "number" ? numberValue(event.target.value) : event.target.value)
        }
      />
    </label>
  );
}

export function findObjectType(config?: ConfigData, objectTypeKey?: string) {
  const objectTypes = config?.object_types ?? [];

  return (
    objectTypes.find((objectType) => objectType.key === objectTypeKey) ??
    objectTypes[0]
  );
}

export function sectionsForObjectType(
  config: ConfigData | undefined,
  objectTypeKey: string | undefined,
  fields: FieldDefinition[]
) {
  const layout = (config?.form_layouts ?? []).find(
    (item) => !item.object_type_key || item.object_type_key === objectTypeKey
  );
  const configuredSections = layout?.sections ?? [];

  if (configuredSections.length > 0) {
    return configuredSections.map((section, index) => ({
      label: section.label || `Section ${index + 1}`,
      fields: section.fields ?? []
    }));
  }

  return [{ label: "Fields", fields: fields.map((field) => field.key) }];
}

function inputType(type: string) {
  if (type === "number" || type === "integer" || type === "decimal") {
    return "number";
  }

  if (type === "date") {
    return "date";
  }

  if (type === "datetime") {
    return "datetime-local";
  }

  return "text";
}

function numberValue(value: string) {
  return value === "" ? null : Number(value);
}

function stringValue(value: RecordValue) {
  if (Array.isArray(value)) {
    return value.join(", ");
  }

  return value === null || value === undefined ? "" : String(value);
}

function humanize(value: string) {
  return value
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}
