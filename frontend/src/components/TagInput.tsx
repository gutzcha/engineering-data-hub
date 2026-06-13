import { FormEvent, KeyboardEvent, useState } from "react";

type TagInputProps = {
  id: string;
  label: string;
  value: string[];
  onChange: (value: string[]) => void;
  placeholder?: string;
};

export function TagInput({
  id,
  label,
  value,
  onChange,
  placeholder
}: TagInputProps) {
  const [draft, setDraft] = useState("");

  const values = value.filter((item) => item.trim().length > 0);

  function addValue(input: string) {
    const token = input.trim();
    if (!token) {
      return;
    }

    if (values.includes(token)) {
      setDraft("");
      return;
    }

    onChange([...values, token]);
    setDraft("");
  }

  function removeValue(index: number) {
    onChange(values.filter((_, position) => position !== index));
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    addValue(draft);
  }

  function keyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter" || event.key === ",") {
      event.preventDefault();
      addValue((event.target as HTMLInputElement).value);
    }
  }

  return (
    <section className="tag-input" aria-label={`${label} filter`}>
      <form className="field-control" onSubmit={submit}>
        <span>{label}</span>
        <input
          id={id}
          aria-label={label}
          type="text"
          value={draft}
          placeholder={placeholder}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={keyDown}
        />
      </form>
      <div className="tag-input-values" role="list" aria-label={`${label} values`}>
        {values.map((item, index) => (
          <button
            className="tag-chip"
            key={`${item}-${index}`}
            type="button"
            onClick={() => removeValue(index)}
            aria-label={`Remove ${label} value ${item}`}
          >
            {item} ×
          </button>
        ))}
      </div>
    </section>
  );
}
