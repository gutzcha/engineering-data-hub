type HttpMethod = "GET" | "POST" | "PATCH" | "DELETE";

type ApiErrorPayload = {
  detail?: string;
  message?: string;
  error?: string;
};

const API_PREFIX = "/api";
const UNSAFE_METHODS = new Set<HttpMethod>(["POST", "PATCH", "DELETE"]);

export async function apiGet<T>(path: string): Promise<T> {
  return request<T>("GET", path);
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  return request<T>("POST", path, body);
}

export async function apiPostForm<T>(path: string, body: FormData): Promise<T> {
  return request<T>("POST", path, body);
}

export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  return request<T>("PATCH", path, body);
}

export async function apiDelete(path: string): Promise<void> {
  await request<void>("DELETE", path);
}

async function request<T>(method: HttpMethod, path: string, body?: unknown): Promise<T> {
  const isFormData = typeof FormData !== "undefined" && body instanceof FormData;
  const response = await fetch(apiUrl(path), {
    cache: "no-store",
    method,
    credentials: "include",
    headers: requestHeaders(method, body, isFormData),
    body:
      body === undefined
        ? undefined
        : isFormData
          ? body
          : JSON.stringify(body)
  });

  if (!response.ok) {
    throw new Error(await errorMessage(response));
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return parseJsonResponse<T>(response);
}

function requestHeaders(method: HttpMethod, body: unknown, isFormData: boolean) {
  const headers: Record<string, string> = {};

  if (body !== undefined && !isFormData) {
    headers["Content-Type"] = "application/json";
  }

  const csrfToken = UNSAFE_METHODS.has(method) ? csrfTokenFromCookie() : "";
  if (csrfToken) {
    headers["X-CSRFToken"] = csrfToken;
  }

  return Object.keys(headers).length ? headers : undefined;
}

function csrfTokenFromCookie() {
  if (typeof document === "undefined") {
    return "";
  }

  const token = document.cookie
    .split(";")
    .map((cookie) => cookie.trim())
    .find((cookie) => cookie.startsWith("csrftoken="));

  return token ? decodeURIComponent(token.slice("csrftoken=".length)) : "";
}

function apiUrl(path: string) {
  if (/^https?:\/\//i.test(path)) {
    return path;
  }

  const normalizedPath = path.startsWith("/") ? path : `/${path}`;

  if (normalizedPath === API_PREFIX || normalizedPath.startsWith(`${API_PREFIX}/`)) {
    return normalizedPath;
  }

  return `${API_PREFIX}${normalizedPath}`;
}

async function errorMessage(response: Response) {
  const fallback = `API request failed with ${response.status} ${response.statusText}`;
  const text = await response.text().catch(() => "");

  try {
    const payload = JSON.parse(text) as ApiErrorPayload;
    const detail = payload.detail ?? payload.message ?? payload.error;
    return detail ? `${fallback}: ${detail}` : fallback;
  } catch {
    return text ? `${fallback}: ${text}` : fallback;
  }
}

async function parseJsonResponse<T>(response: Response) {
  const contentType = response.headers.get("Content-Type") ?? "";
  if (!contentType.toLowerCase().includes("application/json")) {
    throw new Error(
      `API request returned a non-JSON response (${contentType || "unknown content type"}) instead of JSON.`
    );
  }

  return response.json() as Promise<T>;
}
