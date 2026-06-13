import { SearchFilters } from "./searchFilterSchema";

export const defaultSearchType = "all";

export function buildSearchFilters(filters: SearchFilters): SearchFilters {
  return {
    q: filters.q?.trim(),
    type: filters.type ?? defaultSearchType,
    status: filters.status?.trim(),
    object_type_key: filters.object_type_key?.trim(),
    tags: normalizeList(filters.tags),
    application: normalizeList(filters.application),
    resin_family: normalizeList(filters.resin_family),
    color: normalizeList(filters.color),
    project_status: normalizeList(filters.project_status),
    form_fields: normalizeList(filters.form_fields)
  };
}

export function buildSearchParams(filters: SearchFilters) {
  const normalized = buildSearchFilters(filters);
  const params = new URLSearchParams();

  if (normalized.q) {
    params.set("q", normalized.q);
  }
  params.set("type", normalized.type ?? defaultSearchType);
  appendListFilter(params, "status", normalized.status ? [normalized.status] : []);
  appendListFilter(
    params,
    "object_type_key",
    normalized.object_type_key ? [normalized.object_type_key] : []
  );
  appendListFilter(params, "tags", normalized.tags);
  appendListFilter(params, "application", normalized.application);
  appendListFilter(params, "resin_family", normalized.resin_family);
  appendListFilter(params, "color", normalized.color);
  appendListFilter(params, "project_status", normalized.project_status);
  appendListFilter(params, "form_fields", normalized.form_fields);
  return params;
}

export function buildSearchPageUrl(filters: SearchFilters) {
  const params = buildSearchParams(filters);
  const queryString = params.toString();
  return queryString ? `/search?${queryString}` : "/search";
}

export function buildSearchApiUrl(filters: SearchFilters) {
  const params = buildSearchParams(filters);
  const queryString = params.toString();
  return queryString ? `/search/?${queryString}` : "/search/";
}

export function parseSearchFilters(searchParams: URLSearchParams): SearchFilters {
  const queryType = searchParams.get("type") ?? defaultSearchType;

  return buildSearchFilters({
    q: searchParams.get("q") ?? undefined,
    type: isSearchType(queryType) ? queryType : defaultSearchType,
    status: searchParams.get("status") ?? undefined,
    object_type_key: searchParams.get("object_type_key") ?? undefined,
    tags: parseListParam(searchParams, "tags"),
    application: parseListParam(searchParams, "application"),
    resin_family: parseListParam(searchParams, "resin_family"),
    color: parseListParam(searchParams, "color"),
    project_status: parseListParam(searchParams, "project_status"),
    form_fields: parseListParam(searchParams, "form_fields")
  });
}

function appendListFilter(params: URLSearchParams, key: string, values?: string[]) {
  if (!values) {
    return;
  }

  for (const value of values) {
    const trimmed = value.trim();
    if (trimmed) {
      params.append(key, trimmed);
    }
  }
}

function parseListParam(searchParams: URLSearchParams, key: string): string[] | undefined {
  const values = searchParams.getAll(key);
  const list: string[] = [];

  for (const raw of values) {
    const split = raw
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
    for (const value of split) {
      if (!list.includes(value)) {
        list.push(value);
      }
    }
  }

  return list.length ? list : undefined;
}

function normalizeList(values?: string[]) {
  if (!values) {
    return [];
  }
  return values.map((value) => value.trim()).filter(Boolean);
}

function isSearchType(value: string) {
  return (
    value === "all" ||
    value === "records" ||
    value === "documents" ||
    value === "projects" ||
    value === "folder_events"
  );
}
