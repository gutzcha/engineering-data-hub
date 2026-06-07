import { useQuery } from "@tanstack/react-query";
import { FileText, FolderSearch, Search, SquareStack, Workflow } from "lucide-react";
import { FormEvent, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { StatusBadge } from "../../components/StatusBadge";
import { apiGet } from "../../lib/api";

type SearchPayload = {
  records?: SearchResult[];
  documents?: SearchResult[];
  projects?: SearchResult[];
  folder_events?: SearchResult[];
  folder_review_events?: SearchResult[];
  results?: Array<SearchResult & { type?: string; category?: string }>;
};

type SearchResult = {
  id?: string | number;
  title?: string;
  name?: string;
  code?: string;
  status?: string;
  object_type_label?: string;
  record_code?: string;
  path?: string;
  summary?: string;
  snippet?: string;
  url?: string;
};

type SearchGroup = {
  key: "records" | "documents" | "projects" | "folder_events";
  label: string;
  pathPrefix: string;
  empty: string;
  icon: typeof SquareStack;
  results: SearchResult[];
};

export function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const query = searchParams.get("q") ?? "";
  const type = searchParams.get("type") ?? "all";
  const [draftQuery, setDraftQuery] = useState(query);

  const searchQuery = useQuery({
    queryKey: ["search", query, type],
    queryFn: () => apiGet<SearchPayload>(`/search/?q=${encodeURIComponent(query)}&type=${encodeURIComponent(type)}`),
    enabled: query.trim().length > 0
  });

  const groups = groupedResults(searchQuery.data);

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const next = new URLSearchParams(searchParams);
    const trimmedQuery = draftQuery.trim();

    if (trimmedQuery) {
      next.set("q", trimmedQuery);
    } else {
      next.delete("q");
    }

    next.set("type", type);
    setSearchParams(next);
  }

  function updateType(value: string) {
    const next = new URLSearchParams(searchParams);
    next.set("type", value);
    setSearchParams(next);
  }

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
        <div className="segmented-tabs" role="tablist" aria-label="Search result type">
          {["all", "records", "documents", "projects", "folder_events"].map((value) => (
            <button
              className={type === value ? "segmented-tab segmented-tab-active" : "segmented-tab"}
              type="button"
              role="tab"
              aria-selected={type === value}
              key={value}
              onClick={() => updateType(value)}
            >
              {humanize(value)}
            </button>
          ))}
        </div>
      </section>

      {!query && (
        <section className="empty-state">
          <Search aria-hidden="true" size={28} />
          <div>
            <h2>Search across the hub</h2>
            <p>Enter a query to find records, controlled documents, projects, and folder review events.</p>
          </div>
        </section>
      )}

      {searchQuery.error && (
        <div className="admin-alert" role="alert">
          <strong>Search failed</strong>
          <span>{errorMessage(searchQuery.error)}</span>
        </div>
      )}

      {query && (
        <div className="search-results-grid">
          {groups.map((group) => (
            <SearchResultGroup key={group.key} group={group} isLoading={searchQuery.isLoading} />
          ))}
        </div>
      )}
    </div>
  );
}

function SearchResultGroup({
  group,
  isLoading
}: {
  group: SearchGroup;
  isLoading: boolean;
}) {
  const Icon = group.icon;

  return (
    <section className="table-panel search-group" aria-labelledby={`${group.key}-title`}>
      <div className="panel-heading">
        <div>
          <p className="section-kicker">Search results</p>
          <h2 id={`${group.key}-title`}>{group.label}</h2>
        </div>
        <StatusBadge tone={group.results.length ? "active" : "neutral"}>
          {isLoading ? "Loading" : group.results.length}
        </StatusBadge>
      </div>
      <div className="search-result-list" role="list">
        {group.results.length === 0 ? (
          <p className="admin-muted">{isLoading ? "Loading results." : group.empty}</p>
        ) : (
          group.results.map((result) => (
            <Link
              className="search-result"
              to={resultUrl(result, group.pathPrefix)}
              key={result.url ?? result.id ?? `${group.key}-${result.title}`}
            >
              <Icon aria-hidden="true" size={17} />
              <span>
                <strong>{result.title ?? result.name ?? result.summary ?? result.code ?? result.id}</strong>
                <small>{resultSubtitle(result)}</small>
              </span>
              <StatusBadge tone={statusTone(result.status)}>{result.status ?? "open"}</StatusBadge>
            </Link>
          ))
        )}
      </div>
    </section>
  );
}

function groupedResults(payload?: SearchPayload): SearchGroup[] {
  const flattened = payload?.results ?? [];

  return [
    {
      key: "records",
      label: "Records",
      pathPrefix: "/records",
      empty: "No matching records.",
      icon: SquareStack,
      results: payload?.records ?? flattenedByType(flattened, "record", "records")
    },
    {
      key: "documents",
      label: "Documents",
      pathPrefix: "/documents",
      empty: "No matching documents.",
      icon: FileText,
      results: payload?.documents ?? flattenedByType(flattened, "document", "documents")
    },
    {
      key: "projects",
      label: "Projects",
      pathPrefix: "/projects",
      empty: "No matching projects.",
      icon: Workflow,
      results: payload?.projects ?? flattenedByType(flattened, "project", "projects")
    },
    {
      key: "folder_events",
      label: "Folder Review Events",
      pathPrefix: "/tasks/folder-events",
      empty: "No folder review events matched.",
      icon: FolderSearch,
      results:
        payload?.folder_events ??
        payload?.folder_review_events ??
        flattenedByType(flattened, "folder_event", "folder_events")
    }
  ];
}

function flattenedByType(
  results: Array<SearchResult & { type?: string; category?: string }>,
  singular: string,
  plural: string
) {
  return results.filter((result) => result.type === singular || result.type === plural || result.category === singular || result.category === plural);
}

function resultSubtitle(result: SearchResult) {
  return [result.code, result.object_type_label, result.record_code, result.path, result.snippet]
    .filter(Boolean)
    .join(" · ");
}

function resultUrl(result: SearchResult, pathPrefix: string) {
  if (result.url) {
    return normalizeBackendUrl(result.url);
  }

  return `${pathPrefix}/${result.id}`;
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

function humanize(value: string) {
  return value.replace(/[_-]+/g, " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Search request failed.";
}
