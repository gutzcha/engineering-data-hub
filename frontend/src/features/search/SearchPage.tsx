import { useQuery } from "@tanstack/react-query";
import { FileText, FolderSearch, Search, SquareStack, Workflow } from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { TagInput } from "../../components/TagInput";
import { SearchFilters, SEARCH_FILTER_FIELDS } from "./searchFilterSchema";
import { StatusBadge } from "../../components/StatusBadge";
import { apiGet } from "../../lib/api";
import {
  buildSearchApiUrl,
  buildSearchFilters,
  buildSearchParams,
  defaultSearchType,
  parseSearchFilters
} from "./searchUrl";

type SearchPayload = {
  results?: SearchResult[];
  documents?: SearchResult[];
  records?: SearchResult[];
  projects?: SearchResult[];
  folder_events?: SearchResult[];
  folder_review_events?: SearchResult[];
  sections?: SearchSection[];
  count?: number;
};

type SearchResult = {
  id?: string | number;
  title?: string;
  name?: string;
  code?: string;
  status?: string;
  object_type_label?: string;
  object_type_key?: string;
  record_code?: string;
  path?: string;
  summary?: string;
  snippet?: string;
  url?: string;
};

type SearchSection = {
  key: string;
  label: string;
  count: number;
  items: SearchResult[];
};

type SearchGroup = {
  key: "records" | "documents" | "projects" | "folder_events";
  label: string;
  pathPrefix: string;
  empty: string;
  icon: typeof SquareStack;
  results: SearchResult[];
};

type UnifiedSearchResult = SearchResult & {
  resultType: SearchGroup["key"];
  resultLabel: string;
  pathPrefix: string;
  icon: typeof SquareStack;
};

type SearchResultType = NonNullable<SearchFilters["type"]>;

const searchResultTypes: SearchResultType[] = ["all", "records", "documents", "projects", "folder_events"];

const sectionMeta: Record<
  string,
  Omit<SearchGroup, "results">
> = {
  records: {
    key: "records",
    label: "Records",
    pathPrefix: "/records",
    empty: "No matching records.",
    icon: SquareStack
  },
  documents: {
    key: "documents",
    label: "Documents",
    pathPrefix: "/documents",
    empty: "No matching documents.",
    icon: FileText
  },
  projects: {
    key: "projects",
    label: "Projects",
    pathPrefix: "/projects",
    empty: "No matching projects.",
    icon: Workflow
  },
  folder_events: {
    key: "folder_events",
    label: "Folder Review Events",
    pathPrefix: "/tasks/folder-events",
    empty: "No folder review events matched.",
    icon: FolderSearch
  }
};

export function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const activeFilters = useMemo(
    () => parseSearchFilters(searchParams),
    [searchParams.toString()]
  );

  const [draftQuery, setDraftQuery] = useState(activeFilters.q ?? "");
  const [draftType, setDraftType] = useState(activeFilters.type ?? defaultSearchType);
  const [draftStatusFilter, setDraftStatusFilter] = useState(activeFilters.status ?? "");
  const [draftObjectTypeFilter, setDraftObjectTypeFilter] = useState(
    activeFilters.object_type_key ?? ""
  );
  const [draftTags, setDraftTags] = useState(activeFilters.tags ?? []);
  const [draftApplication, setDraftApplication] = useState(activeFilters.application ?? []);
  const [draftResinFamily, setDraftResinFamily] = useState(activeFilters.resin_family ?? []);
  const [draftColor, setDraftColor] = useState(activeFilters.color ?? []);
  const [draftProjectStatus, setDraftProjectStatus] = useState(
    activeFilters.project_status ?? []
  );
  const [draftFormFields, setDraftFormFields] = useState(activeFilters.form_fields ?? []);

  useEffect(() => {
    setDraftQuery(activeFilters.q ?? "");
    setDraftType(activeFilters.type ?? defaultSearchType);
    setDraftStatusFilter(activeFilters.status ?? "");
    setDraftObjectTypeFilter(activeFilters.object_type_key ?? "");
    setDraftTags(activeFilters.tags ?? []);
    setDraftApplication(activeFilters.application ?? []);
    setDraftResinFamily(activeFilters.resin_family ?? []);
    setDraftColor(activeFilters.color ?? []);
    setDraftProjectStatus(activeFilters.project_status ?? []);
    setDraftFormFields(activeFilters.form_fields ?? []);
  }, [
    activeFilters.q,
    activeFilters.type,
    activeFilters.status,
    activeFilters.object_type_key,
    (activeFilters.tags ?? []).join("|"),
    (activeFilters.application ?? []).join("|"),
    (activeFilters.resin_family ?? []).join("|"),
    (activeFilters.color ?? []).join("|"),
    (activeFilters.project_status ?? []).join("|"),
    (activeFilters.form_fields ?? []).join("|")
  ]);

  const searchUrl = buildSearchApiUrl(activeFilters);
  const hasSearchInput = Boolean(
    activeFilters.q ||
      activeFilters.type !== defaultSearchType ||
      activeFilters.status ||
      activeFilters.object_type_key ||
      hasFilters(activeFilters)
  );
  const searchQuery = useQuery({
    queryKey: ["search", searchUrl],
    queryFn: () => apiGet<SearchPayload>(searchUrl),
    enabled: hasSearchInput
  });

  const groups = groupedResults(searchQuery.data, activeFilters.type);
  const hasActiveFilters = Boolean(
    activeFilters.status ||
      activeFilters.object_type_key ||
      hasFilters(activeFilters)
  );
  const unifiedResults = unifiedSearchResults(groups);

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextFilters = buildSearchFilters({
      q: draftQuery,
      type: draftType,
      status: draftStatusFilter,
      object_type_key: draftObjectTypeFilter,
      tags: draftTags,
      application: draftApplication,
      resin_family: draftResinFamily,
      color: draftColor,
      project_status: draftProjectStatus,
      form_fields: draftFormFields
    });
    setSearchParams(buildSearchParams(nextFilters));
  }

  function updateType(value: SearchResultType) {
    setDraftType(value);
    const nextFilters = buildSearchParams({ ...activeFilters, type: value });
    setSearchParams(nextFilters);
  }

  const filterFieldMap = {
    tags: draftTags,
    application: draftApplication,
    resin_family: draftResinFamily,
    color: draftColor,
    project_status: draftProjectStatus,
    form_fields: draftFormFields
  };

  return (
    <div className="page-stack search-page">
      <section className="workspace-header" aria-labelledby="search-title">
        <div>
          <p className="section-kicker">Cross-system discovery</p>
          <h1 id="search-title">Search</h1>
        </div>
      </section>

      <section className="filter-panel" aria-label="Unified search controls">
        <form className="search-form" onSubmit={submitSearch}>
          <label className="field-control field-control-wide">
            <span>Search query</span>
            <input
              aria-label="Search query"
              value={draftQuery}
              onChange={(event) => setDraftQuery(event.target.value)}
            />
          </label>
          <button className="button button-primary" type="submit">
            <Search aria-hidden="true" size={16} />
            Search
          </button>
        </form>
        <div className="search-filter-layout">
          {SEARCH_FILTER_FIELDS.map((field) => (
            <TagInput
              key={field.key}
              id={`search-filter-${field.key}`}
              label={field.label}
              value={filterFieldMap[field.key as keyof typeof filterFieldMap]}
              onChange={(next) =>
                updateFilterList(field.key, next, {
                  tags: setDraftTags,
                  application: setDraftApplication,
                  resin_family: setDraftResinFamily,
                  color: setDraftColor,
                  project_status: setDraftProjectStatus,
                  form_fields: setDraftFormFields
                })
              }
            />
          ))}
          <label className="field-control">
            <span>Status</span>
            <input
              aria-label="Filter status"
              value={draftStatusFilter}
              onChange={(event) => setDraftStatusFilter(event.target.value)}
            />
          </label>
          <label className="field-control">
            <span>Object Type</span>
            <input
              aria-label="Filter object type"
              value={draftObjectTypeFilter}
              onChange={(event) => setDraftObjectTypeFilter(event.target.value)}
            />
          </label>
        </div>
        <div className="segmented-tabs" role="tablist" aria-label="Search result type">
          {searchResultTypes.map((value) => (
            <button
              className={draftType === value ? "segmented-tab segmented-tab-active" : "segmented-tab"}
              type="button"
              role="tab"
              aria-selected={draftType === value}
              key={value}
              onClick={() => updateType(value)}
            >
              {humanize(value)}
            </button>
          ))}
        </div>
        <div className="active-filter-row" aria-label="Active search filters">
          {activeFilters.status ? <StatusBadge tone="review">Status: {activeFilters.status}</StatusBadge> : null}
          {activeFilters.object_type_key ? (
            <StatusBadge tone="ready">Type: {humanize(activeFilters.object_type_key)}</StatusBadge>
          ) : null}
          {activeFilters.tags?.length ? (
            <StatusBadge tone="active">Tags: {activeFilters.tags.join(", ")}</StatusBadge>
          ) : null}
          {activeFilters.application?.length ? (
            <StatusBadge tone="active">Application: {activeFilters.application.join(", ")}</StatusBadge>
          ) : null}
          {activeFilters.resin_family?.length ? (
            <StatusBadge tone="active">
              Resin Family: {activeFilters.resin_family.join(", ")}
            </StatusBadge>
          ) : null}
          {activeFilters.color?.length ? (
            <StatusBadge tone="active">Color: {activeFilters.color.join(", ")}</StatusBadge>
          ) : null}
          {activeFilters.project_status?.length ? (
            <StatusBadge tone="active">
              Project Status: {activeFilters.project_status.join(", ")}
            </StatusBadge>
          ) : null}
          {activeFilters.form_fields?.length ? (
            <StatusBadge tone="active">Form Fields: {activeFilters.form_fields.join(", ")}</StatusBadge>
          ) : null}
          {hasActiveFilters ? (
            <StatusBadge tone="active">{activeFilters.q ? "Prefiltered" : "Filtered by params"}</StatusBadge>
          ) : null}
        </div>
      </section>

      {!hasSearchInput && (
        <section className="empty-state">
          <Search aria-hidden="true" size={28} />
          <div>
            <h2>Search across the hub</h2>
            <p>Enter a query or apply a status/object type filter to find records, documents, projects, and folder review events.</p>
          </div>
        </section>
      )}

      {searchQuery.error && (
        <div className="admin-alert" role="alert">
          <strong>Search failed</strong>
          <span>{errorMessage(searchQuery.error)}</span>
        </div>
      )}

      {hasSearchInput && (
        <SearchResultList results={unifiedResults} isLoading={searchQuery.isLoading} />
      )}
    </div>
  );
}

function SearchResultList({
  results,
  isLoading
}: {
  results: UnifiedSearchResult[];
  isLoading: boolean;
}) {
  return (
    <section className="table-panel search-group" aria-labelledby="search-results-title">
      <div className="panel-heading">
        <div>
          <p className="section-kicker">Search results</p>
          <h2 id="search-results-title">Unified Results</h2>
        </div>
        <StatusBadge tone={results.length ? "active" : "neutral"}>
          {isLoading ? "Loading" : results.length}
        </StatusBadge>
      </div>
      <div className="search-result-list" role="list">
        {results.length === 0 ? (
          <p className="admin-muted">
            {isLoading ? "Loading results." : "No active results for this query."}
          </p>
        ) : (
          results.map((result) => {
            const Icon = result.icon;
            const itemUrl = resultUrl(result, result.pathPrefix) ?? "#";
            return (
              <Link
                className="search-result"
                to={itemUrl}
                key={
                  result.url ??
                  result.id ??
                  `${result.resultType}-${result.title}-${result.code ?? ""}`
                }
              >
                <Icon aria-hidden="true" size={17} />
                <span>
                  <strong>{result.title ?? result.name ?? result.summary ?? result.code ?? result.id}</strong>
                  <small>{resultSubtitle(result)}</small>
                </span>
                <StatusBadge tone="neutral">{result.resultLabel}</StatusBadge>
                <StatusBadge tone={statusTone(result.status)}>{result.status ?? "open"}</StatusBadge>
              </Link>
            );
          })
        )}
      </div>
    </section>
  );
}

function unifiedSearchResults(groups: SearchGroup[]): UnifiedSearchResult[] {
  return groups.flatMap((group) =>
    group.results
      .filter((result) => Boolean(resultUrl(result, group.pathPrefix)))
      .map((result) => ({
        ...result,
        resultType: group.key,
        resultLabel: group.label,
        pathPrefix: group.pathPrefix,
        icon: group.icon
      }))
  );
}

function groupedResults(
  payload?: SearchPayload,
  activeType: SearchFilters["type"] = defaultSearchType
): SearchGroup[] {
  const sections = payload?.sections;
  const typeFilter = activeType === "all" ? undefined : activeType;

  if (Array.isArray(sections) && sections.length > 0) {
    const sectionGroups = sections
      .map((section) => {
        const metadata = sectionMeta[section.key];
        if (!metadata) {
          return null;
        }

        return {
          ...metadata,
          results: section.items ?? []
        };
      })
      .filter((group): group is SearchGroup => group !== null && group.results.length > 0);

    if (typeFilter) {
      return sectionGroups.filter((group) => group.key === typeFilter);
    }

    return sectionGroups;
  }

  const flattened = payload?.results ?? [];
  const allCandidates: SearchGroup[] = [
    {
      ...sectionMeta.records,
      results: payload?.records ?? flattenedByType(flattened, "record", "records")
    },
    {
      ...sectionMeta.documents,
      results: payload?.documents ?? flattenedByType(flattened, "document", "documents")
    },
    {
      ...sectionMeta.projects,
      results: payload?.projects ?? flattenedByType(flattened, "project", "projects")
    },
    {
      ...sectionMeta.folder_events,
      results:
        payload?.folder_events ??
        payload?.folder_review_events ??
        flattenedByType(flattened, "folder_event", "folder_events")
    }
  ];

  if (typeFilter) {
    const match = allCandidates.find((group) => group.key === typeFilter);
    return match && match.results.length > 0 ? [match] : [];
  }

  return allCandidates.filter((group) => group.results.length > 0);
}

function flattenedByType(
  results: Array<SearchResult & { type?: string; category?: string }>,
  singular: string,
  plural: string
) {
  return results.filter(
    (result) => result.type === singular || result.type === plural || result.category === singular || result.category === plural
  );
}

function resultSubtitle(result: SearchResult) {
  return [result.code, result.object_type_label, result.record_code, result.path, result.snippet]
    .filter(Boolean)
    .join(" · ");
}

function resultUrl(result: SearchResult, pathPrefix: string) {
  if (result.url) {
    const normalized = normalizeBackendUrl(result.url);
    if (normalized) {
      return normalized;
    }
  }

  if (result.id) {
    return `${pathPrefix}/${result.id}`;
  }

  if (result.record_code) {
    return `${pathPrefix}/${result.record_code}`;
  }

  return undefined;
}

function normalizeBackendUrl(url: string) {
  const withoutApiPrefix = url.replace(/^\/api(?=\/)/, "");
  const withoutTrailingSlash =
    withoutApiPrefix.length > 1 ? withoutApiPrefix.replace(/\/$/, "") : withoutApiPrefix;

  if (withoutTrailingSlash.startsWith("/folder-events/")) {
    return withoutTrailingSlash.replace("/folder-events/", "/tasks/folder-events/");
  }

  return withoutTrailingSlash;
}

function statusTone(status?: string) {
  if (status === "released" || status === "ready" || status === "active") {
    return "ready";
  }

  if (status === "blocked") {
    return "blocked";
  }

  if (status === "review" || status === "draft") {
    return "review";
  }

  return "neutral";
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Search request failed.";
}

function humanize(value: string) {
  return value.replace(/[_-]+/g, " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

function updateFilterList(
  filterKey: keyof SearchFilters,
  next: string[],
  handlers: {
    tags: (value: string[]) => void;
    application: (value: string[]) => void;
    resin_family: (value: string[]) => void;
    color: (value: string[]) => void;
    project_status: (value: string[]) => void;
    form_fields: (value: string[]) => void;
  }
) {
  switch (filterKey) {
    case "tags":
      handlers.tags(next);
      break;
    case "application":
      handlers.application(next);
      break;
    case "resin_family":
      handlers.resin_family(next);
      break;
    case "color":
      handlers.color(next);
      break;
    case "project_status":
      handlers.project_status(next);
      break;
    case "form_fields":
      handlers.form_fields(next);
      break;
    default:
      break;
  }
}

function hasFilters(filters: SearchFilters) {
  return (
    (filters.tags?.length ?? 0) > 0 ||
    (filters.application?.length ?? 0) > 0 ||
    (filters.resin_family?.length ?? 0) > 0 ||
    (filters.color?.length ?? 0) > 0 ||
    (filters.project_status?.length ?? 0) > 0 ||
    (filters.form_fields?.length ?? 0) > 0
  );
}
