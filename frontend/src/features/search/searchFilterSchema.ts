export type SearchFilters = {
  q?: string;
  type?: "all" | "records" | "documents" | "projects" | "folder_events";
  status?: string;
  object_type_key?: string;
  tags?: string[];
  application?: string[];
  resin_family?: string[];
  color?: string[];
  project_status?: string[];
  form_fields?: string[];
};

export type SearchFilterKey =
  | "tags"
  | "application"
  | "resin_family"
  | "color"
  | "project_status"
  | "form_fields";

export type SearchFilterField = {
  key: SearchFilterKey;
  label: string;
};

export const SEARCH_FILTER_FIELDS: SearchFilterField[] = [
  { key: "tags", label: "Tags" },
  { key: "application", label: "Application" },
  { key: "resin_family", label: "Resin Family" },
  { key: "color", label: "Color" },
  { key: "project_status", label: "Project Status" },
  { key: "form_fields", label: "Form Fields" }
];
