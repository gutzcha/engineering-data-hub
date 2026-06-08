import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";

const packageJson = JSON.parse(
  readFileSync(resolve(process.cwd(), "package.json"), "utf8")
) as { scripts: Record<string, string> };
const dockerfile = readFileSync(
  resolve(process.cwd(), "Dockerfile"),
  "utf8"
);
const styles = readFileSync(resolve(process.cwd(), "src/styles.css"), "utf8");

describe("App shell", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders route-aware navigation for the operational sections", () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify({ detail: "Authentication required" }), { status: 403 }))
    );

    render(<App />);

    const navigation = screen.getByRole("navigation", {
      name: /primary navigation/i
    });

    [
      "Home",
      "Records",
      "Projects",
      "Documents",
      "Search",
      "Dashboards",
      "Tasks",
      "Admin"
    ].forEach((section) => {
      expect(
        within(navigation).getByRole("link", { name: section })
      ).toBeInTheDocument();
    });

    expect(within(navigation).getByRole("link", { name: "Home" })).toHaveAttribute(
      "aria-current",
      "page"
    );
    expect(
      screen.getByRole("heading", { name: "Operational Overview" })
    ).toBeInTheDocument();
  });

  it("renders Home operational metrics and recent activity from live API data", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = typeof input === "string" ? input : input.toString();

        if (url.endsWith("/api/accounts/me/")) {
          return jsonResponse({ detail: "Authentication required" }, 403);
        }

        if (url.endsWith("/api/records/")) {
          return jsonResponse([
            {
              id: "rec-1",
              code: "MAT-001",
              title: "Polycarbonate resin",
              owner: "Materials Lab",
              status: "draft",
              updated_at: "2026-06-07T09:00:00Z"
            },
            {
              id: "rec-2",
              code: "MAT-002",
              title: "Released ABS grade",
              owner: "Quality",
              status: "released",
              updated_at: "2026-06-08T08:30:00Z"
            },
            {
              id: "rec-3",
              code: "MAT-003",
              title: "Archived legacy PP",
              owner: "Engineering",
              status: "archived",
              updated_at: "2026-06-08T10:00:00Z"
            }
          ]);
        }

        if (url.endsWith("/api/workflow-tasks/?state=open")) {
          return jsonResponse([
            {
              id: 101,
              title: "Review PC data sheet",
              state: "open",
              due_date: "2000-01-01T12:00:00Z"
            },
            {
              id: 102,
              title: "Approve ABS release",
              state: "open",
              due_date: "2099-06-12T12:00:00Z"
            }
          ]);
        }

        if (url.endsWith("/api/documents/")) {
          return jsonResponse([{ id: 201, title: "PC technical data sheet" }]);
        }

        return jsonResponse({ detail: `Unhandled test URL ${url}` }, 404);
      })
    );

    render(<App />);

    expect(await screen.findByRole("link", { name: /open records\s*2/i })).toHaveAttribute(
      "href",
      "/records"
    );
    expect(screen.getByRole("link", { name: /pending review\s*2/i })).toHaveAttribute(
      "href",
      "/tasks"
    );
    expect(screen.getByRole("link", { name: /overdue work\s*1/i })).toHaveAttribute(
      "href",
      "/tasks?due=overdue"
    );
    expect(screen.getByRole("link", { name: /controlled documents\s*1/i })).toHaveAttribute(
      "href",
      "/documents"
    );

    expect(screen.getByRole("link", { name: "MAT-003" })).toHaveAttribute(
      "href",
      "/records/rec-3"
    );
    expect(screen.getByRole("link", { name: "MAT-002" })).toHaveAttribute(
      "href",
      "/records/rec-2"
    );
    expect(screen.getByText("Archived legacy PP")).toBeInTheDocument();

    expect(screen.queryByText("PE-1042")).not.toBeInTheDocument();
    expect(screen.queryByText("Today")).not.toBeInTheDocument();
    expect(screen.queryByText("Yesterday")).not.toBeInTheDocument();
  });

  it("uses built frontend assets for the production container start path", () => {
    expect(packageJson.scripts.start).toContain("vite preview");
    expect(dockerfile).toMatch(/npm run build/);
  });

  it("keeps narrow viewports usable without page-level horizontal overflow", () => {
    expect(styles).not.toMatch(/body\s*{[^}]*min-width\s*:/s);
    expect(styles).toContain("@media (max-width: 900px)");
    expect(styles).toMatch(/\.app-shell\s*{[^}]*grid-template-columns:\s*1fr/s);
  });
});

function jsonResponse(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" }
  });
}
