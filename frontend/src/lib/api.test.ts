/*
 * ===
 * File Summary
 * Path: frontend\src\lib\api.test.ts
 * Type: typescript
 * Purpose: Shared frontend API and utility layer used by feature modules.
 * Primary responsibilities:
 * - Domain behavior is summarized for fast onboarding and avoids full-file reread.
 * - Core symbols: inferred from domain responsibilities
 * Inputs:
 * - Downstream and upstream interactions in the same domain.
 * Outputs:
 * - API payloads, records, side effects, or UI views depending on file role.
 * Dependencies:
 * - Shared runtime services and adjacent domain modules.
 * Known risks:
 * - Validate behavior after migrations, dependency upgrades, or contract changes.
 * ===
 * 
 */

import { afterEach, describe, expect, it, vi } from "vitest";

import { apiGet, apiPost, apiPostForm } from "./api";

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" }
  });
}

describe("api client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    document.cookie = "csrftoken=; Max-Age=0; path=/";
  });

  it("sends cookies with safe requests", async () => {
    const fetchMock = vi.fn(async () => jsonResponse({ ok: true }));
    vi.stubGlobal("fetch", fetchMock);

    await apiGet("/accounts/me/");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/accounts/me/",
      expect.objectContaining({
        credentials: "include",
        method: "GET"
      })
    );
  });

  it("adds the csrf token to unsafe json requests", async () => {
    document.cookie = "csrftoken=session-token";
    const fetchMock = vi.fn(async () => jsonResponse({ ok: true }));
    vi.stubGlobal("fetch", fetchMock);

    await apiPost("/records/", { title: "Film" });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/records/",
      expect.objectContaining({
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": "session-token"
        },
        method: "POST"
      })
    );
  });

  it("does not force a content type for form uploads", async () => {
    document.cookie = "csrftoken=upload-token";
    const form = new FormData();
    form.append("title", "Spec");
    const fetchMock = vi.fn(async () => jsonResponse({ ok: true }));
    vi.stubGlobal("fetch", fetchMock);

    await apiPostForm("/documents/", form);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/documents/",
      expect.objectContaining({
        body: form,
        credentials: "include",
        headers: {
          "X-CSRFToken": "upload-token"
        },
        method: "POST"
      })
    );
  });

  it("reports a clear error when a successful response is not json", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response("<!doctype html><title>App</title>", {
            status: 200,
            headers: { "Content-Type": "text/html" }
          })
      )
    );

    await expect(apiGet("/projects/workload/")).rejects.toThrow(
      /non-JSON response.*instead of JSON/i
    );
  });
});

