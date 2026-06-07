type HttpMethod = "GET" | "POST" | "PATCH" | "DELETE";

type ApiErrorPayload = {
  detail?: string;
  message?: string;
  error?: string;
};

const API_PREFIX = "/api";

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
    method,
    headers: body === undefined || isFormData ? undefined : { "Content-Type": "application/json" },
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

  return response.json() as Promise<T>;
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
